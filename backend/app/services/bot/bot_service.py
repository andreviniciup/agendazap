"""
Motor principal do bot: normalização, intenção, estado e decisão
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import difflib
import re
import unicodedata

from app.services.bot.intent_rules import DEFAULT_RULES, Intent, normalize_and_correct
from app.services.bot.conversation_state import ConversationState
from app.services.bot.data_collector import DataCollector, LabelQuality
from app.services.bot.bot_classifier import BotClassifier
from app.services.bot.affirmation_analyzer import AffirmationAnalyzer, AffirmationType
from app.services.bot import templates
from app.services.bot import parser
from app.services.bot.smart_templates import get_smart_response, get_follow_up_questions, get_contextual_response
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.appointment_service import AppointmentService
from app.services.plan_service import PlanService
from app.dependencies import get_redis
from app.schemas.appointment import PublicAppointmentCreate
from app.models.client import Client
from app.models.user import User


class IntentEngine:
    def __init__(self) -> None:
        self.rules = DEFAULT_RULES

    def detect(self, text: str) -> Tuple[str, Dict[str, Any], float]:
        if not text:
            return Intent.UNKNOWN, {}, 0.0
        normalized = normalize_and_correct(text)

        best_intent = Intent.UNKNOWN
        best_score = 0.0
        entities: Dict[str, Any] = {}

        for rule in self.rules:
            score = 0.0

            # regex patterns
            for pat in rule.patterns:
                if pat.search(normalized):
                    score += 0.6
                    break

            # synonyms with fuzzy match tolerance
            for syn in rule.synonyms:
                ratio = difflib.SequenceMatcher(None, normalized, syn).ratio()
                if ratio > 0.65 or syn in normalized:
                    score += 0.3
                    break

            # negative keywords reduce confidence
            for neg in rule.negative_keywords:
                if neg in normalized:
                    score -= 0.4

            # extract simple entities when pattern exists
            if score > 0.0 and rule.entity_patterns:
                for k, epat in rule.entity_patterns.items():
                    m = epat.search(normalized)
                    if m:
                        entities[k] = m.group(0)

            if score > best_score:
                best_score = score
                best_intent = rule.name

        return best_intent, entities, max(0.0, min(best_score, 1.0))


class BotService:
    def __init__(self, redis_client) -> None:
        self.state = ConversationState(redis_client)
        self.intent_engine = IntentEngine()
        self.collector = DataCollector()  # Sistema de coleta de dados para ML
        self.classifier = BotClassifier()  # Classificador ML (se disponível)
        self.affirmation_analyzer = AffirmationAnalyzer()  # Analisador de afirmações

    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize incoming
        wa_number = payload.get("from")
        
        # Extrair texto do payload (pode vir de diferentes formatos)
        text = ""
        if "text" in payload:
            text = payload.get("text", "").strip()
        elif "messages" in payload and payload["messages"]:
            text = payload["messages"][0].get("text", {}).get("body", "").strip()
        
        print(f"📝 TEXTO RECEBIDO: '{text}'")
        
        # Analisar afirmações e negações
        affirmation_analysis = self.affirmation_analyzer.analyze_affirmation(text)
        print(f"💭 AFIRMAÇÃO: {affirmation_analysis['type'].value} (intensidade: {affirmation_analysis['intensity']:.1f})")
        
        now = datetime.utcnow()
        tone = "night" if templates.is_night(now) else "day"

        conv = await self.state.load(wa_number)
        # registrar último texto para o parser
        slots = conv.get("slots", {})
        slots["text"] = text
        # Guardar metadados do payload para resoluções posteriores
        if payload.get("to"):
            slots["to"] = payload.get("to")
        if payload.get("from"):
            slots["from"] = payload.get("from")
            slots.setdefault("client_whatsapp", payload.get("from"))
        conv["slots"] = slots
        await self.state.save(wa_number, conv)
        # State-first handling: se estamos coletando slots, priorizar isso
        conv_state = conv.get("state", "idle")
        if conv_state == "asking_date":
            extracted_date = parser.parse_date_from_text(text, now)
            if extracted_date:
                slots["date"] = extracted_date.isoformat()
                conv["slots"] = slots
                conv["state"] = "asking_window"
                await self.state.save(wa_number, conv)
                return {"to_number": wa_number, "message": "Prefere manhã ou tarde?"}
        elif conv_state == "asking_window":
            win = parser.parse_window_from_text(text)
            if win:
                slots["window"] = win
                conv["slots"] = slots
                conv["state"] = "asking_time"
                await self.state.save(wa_number, conv)
                suggested = await self._suggest_real_slots(slots)
                options_text = suggested or "10h ou 14h"
                return {"to_number": wa_number, "message": templates.pick("availability", tone, time_options=options_text)}
        elif conv_state == "asking_time":
            t = parser.parse_time_from_text(text)
            if t:
                slots["time"] = f"{t.hour:02d}:{t.minute:02d}" if t.minute else f"{t.hour:02d}h"
                conv["slots"] = slots
                await self.state.save(wa_number, conv)
                created_msg = await self._try_create_appointment(slots, tone)
                if created_msg:
                    conv["state"] = "idle"
                    await self.state.save(wa_number, conv)
                    return {"to_number": wa_number, "message": created_msg}
                return {"to_number": wa_number, "message": templates.pick("confirm", tone, date=slots.get("date", ""), time=slots.get("time", ""), service_name="o serviço")}

        # 1. TENTA REGRA (rápido)
        intent, entities, confidence = self.intent_engine.detect(text)
        source = "rule"
        
        # Debug: mostrar resultado da regra
        print(f"🔍 REGRA: {intent} ({confidence:.2%}) - '{text}'")
        
        # 2. SEMPRE TENTA ML PARA FRASES LONGAS OU SE REGRA INCERTA
        use_ml = (
            self.classifier.ready and (
                confidence < 0.8 or  # Regra incerta
                len(text.split()) > 3 or  # Frase longa
                confidence < 0.6  # Regra com baixa confiança
            )
        )
        
        if use_ml:
            intent_ml, confidence_ml = self.classifier.classify(text)
            print(f"🤖 ML: {intent_ml} ({confidence_ml:.2%})")
            
            # Se ML mais confiante que regra OU se regra muito incerta
            if confidence_ml > 0.6 and (confidence_ml > confidence or confidence < 0.5):
                intent = intent_ml
                confidence = confidence_ml
                source = "ml"
                print(f"✅ USANDO ML: {intent} ({confidence:.2%})")
            else:
                print(f"❌ MANTENDO REGRA: {intent} ({confidence:.2%})")
        else:
            print(f"⏭️ PULANDO ML (classifier.ready={self.classifier.ready})")

        # Determinar qualidade de etiqueta para ML
        if confidence > 0.8:
            label_quality = LabelQuality.CONFIDENT.value
        elif confidence < 0.3:
            label_quality = LabelQuality.UNCERTAIN.value
        else:
            label_quality = LabelQuality.UNCERTAIN.value
        
        # Logar interação para treino futuro de ML
        try:
            self.collector.log_interaction(
                text=text,
                intent=intent,
                confidence=confidence,
                label_quality=label_quality,
                user_whatsapp=wa_number,
                context={
                    'entities': entities,
                    'slots': slots,
                    'state': conv_state,
                    'timestamp': now.isoformat(),
                    'source': source  # 'rule' ou 'ml'
                },
                resolved=False
            )
        except Exception:
            # Não deixar coleta de dados quebrar o bot
            pass

        # policy: clarify on medium confidence
        if 0.3 <= confidence < 0.6:
            conv["fail_count"] = conv.get("fail_count", 0) + 1
            await self.state.save(wa_number, conv)
            message = get_smart_response(
                intent="unknown",
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": entities.get("service_name", "o serviço")
                }
            )
            return {"to_number": wa_number, "message": message}

        # low confidence → se estamos em estado de coleta, manter pergunta; senão greeting
        if confidence < 0.3:
            conv["fail_count"] = conv.get("fail_count", 0) + 1
            await self.state.save(wa_number, conv)
            if conv_state in ("asking_date", "asking_window", "asking_time"):
                # repetir a última pergunta de forma curta
                if conv_state == "asking_date":
                    return {"to_number": wa_number, "message": "Quer para hoje ou amanhã?"}
                if conv_state == "asking_window":
                    return {"to_number": wa_number, "message": "Manhã ou tarde?"}
                return {"to_number": wa_number, "message": "Qual horário você prefere?"}
            
            # Usar template inteligente para baixa confiança
            message = get_smart_response(
                intent="greeting",
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": "nossos serviços"
                }
            )
            return {"to_number": wa_number, "message": message}

        # High confidence → handle intents
        conv["last_intent"] = intent
        conv["fail_count"] = 0
        await self.state.save(wa_number, conv)

        if intent == Intent.HUMAN:
            # Usar template inteligente para atendimento humano
            message = get_smart_response(
                intent="human", 
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": entities.get("service_name", "")
                }
            )
            return {"to_number": wa_number, "message": message, "handoff": True}

        if intent == Intent.PRICE:
            # Usar template inteligente para preços
            db: Session = next(get_db())
            user_id = await self._resolve_user_id(slots, db)
            service_name = "o serviço"
            price_info = "R$ —"
            
            if user_id:
                svc = await self._match_service_from_text(user_id, slots.get("text", ""), db)
                if svc:
                    name, price = svc[0], svc[1]
                    service_name = name
                    price_info = f"R$ {float(price):.2f}" if price is not None else "sob consulta"
            
            message = get_smart_response(
                intent="price",
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": service_name,
                    "price": price_info
                }
            )
            
            # Adicionar pergunta de acompanhamento se confiança alta
            if confidence > 0.8:
                follow_ups = get_follow_up_questions("price", confidence)
                if follow_ups:
                    message += f"\n\n{follow_ups[0]}"
            
            return {"to_number": wa_number, "message": message}

        if intent == Intent.SERVICES:
            # Usar template inteligente para serviços
            listing = await self._list_services(slots, include_description=True)
            if listing:
                # Se temos lista de serviços, usar template inteligente como prefixo
                smart_message = get_smart_response(
                    intent="services",
                    confidence=confidence,
                    context={
                        "user_name": slots.get("first_name", ""),
                        "service_name": "nossos serviços"
                    }
                )
                return {"to_number": wa_number, "message": f"{smart_message}\n\n{listing}"}
            
            message = get_smart_response(
                intent="services",
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": "nossos serviços"
                }
            )
            
            # Adicionar pergunta de acompanhamento
            follow_ups = get_follow_up_questions("services", confidence)
            if follow_ups:
                message += f"\n\n{follow_ups[0]}"
            
            return {"to_number": wa_number, "message": message}

        if intent == Intent.ABOUT:
            # Usar template inteligente para informações
            db: Session = next(get_db())
            user_id = await self._resolve_user_id(slots, db)
            service_info = ""
            
            if user_id:
                rows = db.execute(
                    "SELECT name, description FROM services WHERE user_id = :uid AND is_active = 1 ORDER BY sort_order, name",
                    {"uid": user_id},
                ).fetchall()
                if rows:
                    if len(rows) == 1:
                        name, desc = rows[0][0], rows[0][1] or ""
                        brief = self._truncate_description(desc)
                        service_info = f"O serviço {name} funciona assim: {brief}"
            
            message = get_smart_response(
                intent="about",
                confidence=confidence,
                context={
                    "user_name": slots.get("first_name", ""),
                    "service_name": "nossos serviços",
                    "service_info": service_info
                }
            )
            
            # Adicionar informação específica se disponível
            if service_info:
                message += f"\n\n{service_info}"
            
            # Adicionar pergunta de acompanhamento
            follow_ups = get_follow_up_questions("about", confidence)
            if follow_ups:
                message += f"\n\n{follow_ups[0]}"
            
            return {"to_number": wa_number, "message": message}

        if intent in (Intent.AVAILABILITY, Intent.SCHEDULE, Intent.RESCHEDULE):
            # Slot filling simplificado: coletar data/hora e confirmar
            return await self._handle_schedule_like(wa_number, conv, intent, tone)

        # Default fallback - usar template inteligente com análise de afirmação
        base_message = get_smart_response(
            intent="greeting",
            confidence=confidence,
            context={
                "user_name": slots.get("first_name", ""),
                "service_name": "nossos serviços"
            }
        )
        
        # Adicionar modificador baseado na análise de afirmação
        affirmation_modifier = self.affirmation_analyzer.get_response_modifier(affirmation_analysis)
        
        # Combinar mensagem base com modificador de afirmação
        if affirmation_analysis["type"] in [AffirmationType.POSITIVE, AffirmationType.CONFIRMATION]:
            message = f"{affirmation_modifier} {base_message}"
        elif affirmation_analysis["type"] in [AffirmationType.NEGATIVE, AffirmationType.REJECTION]:
            message = f"{affirmation_modifier} {base_message}"
        elif affirmation_analysis["type"] == AffirmationType.UNCERTAIN:
            message = f"{affirmation_modifier} {base_message}"
        else:
            message = base_message
        
        return {"to_number": wa_number, "message": message}

    async def _handle_schedule_like(self, wa_number: str, conv: Dict[str, Any], intent: str, tone: str) -> Dict[str, Any]:
        slots = conv.get("slots", {})

        # 1) Coletar data simples (amanhã/hoje/weekday) – placeholder simplificado
        if "date" not in slots:
            # tenta extrair do último texto
            # nota: depende do chamador setar slots['text'] antes; se não, pergunta
            extracted = parser.parse_date_from_text(slots.get("text", ""))
            if extracted is None:
                conv["state"] = "asking_date"
                await self.state.save(wa_number, conv)
                return {"to_number": wa_number, "message": "Quer para hoje ou amanhã?"}
            slots["date"] = extracted.isoformat()
            conv["slots"] = slots
            await self.state.save(wa_number, conv)

        # 2) Coletar janela
        if "window" not in slots:
            win = parser.parse_window_from_text(slots.get("text", ""))
            if not win:
                # tentar usar preferência do cliente
                client_pref_window = await self._resolve_client_preferred_window(slots)
                if client_pref_window:
                    slots["window"] = client_pref_window
                else:
                    conv["state"] = "asking_window"
                    await self.state.save(wa_number, conv)
                    return {"to_number": wa_number, "message": "Prefere manhã ou tarde?"}
            else:
                slots["window"] = win
            conv["slots"] = slots
            await self.state.save(wa_number, conv)

        # 3) Confirmar horário
        if "time" not in slots:
            # sugerir horários reais se possível e entrar em estado de coleta de horário
            suggested = await self._suggest_real_slots(slots)
            options_text = suggested or "10h ou 14h"
            msg = templates.pick("availability", tone, time_options=options_text)
            conv["state"] = "asking_time"
            await self.state.save(wa_number, conv)
            return {"to_number": wa_number, "message": msg}

        # 4) Criar agendamento real se possível
        created_msg = await self._try_create_appointment(slots, tone)
        if created_msg:
            return {"to_number": wa_number, "message": created_msg}
        else:
            msg = templates.pick("confirm", tone, date=slots.get("date", ""), time=slots.get("time", ""), service_name="o serviço")
            return {"to_number": wa_number, "message": msg}

    async def _suggest_real_slots(self, slots: Dict[str, Any]) -> Optional[str]:
        try:
            user_id = slots.get("user_id")
            service_id = slots.get("service_id")
            date_iso = slots.get("date")
            if not (user_id and service_id and date_iso):
                return None
            # obter sessão
            db: Session = next(get_db())
            # construir serviços auxiliares mínimos
            plan_service = PlanService(db, None)
            appt_service = AppointmentService(db, plan_service)
            target_date = datetime.fromisoformat(date_iso).date()
            times = appt_service.get_available_slots(user_id, service_id, target_date)

            # filtrar por janela solicitada ou preferência do cliente
            win = slots.get("window") or await self._resolve_client_preferred_window(slots)
            if win and times:
                def in_window(t):
                    if win == "morning":
                        return 8 <= t.hour < 12
                    if win == "afternoon":
                        return 12 <= t.hour < 18
                    if win == "evening":
                        return 18 <= t.hour <= 21
                    return True
                times = [t for t in times if in_window(t)] or times
            if not times:
                return None
            # gerar duas opções legíveis
            formatted = [f"{t.hour:02d}h" if t.minute == 0 else f"{t.hour:02d}:{t.minute:02d}" for t in times[:2]]
            return " ou ".join(formatted)
        except Exception:
            return None

    async def _list_services(self, slots: Dict[str, Any], include_description: bool = False) -> Optional[str]:
        try:
            user_id = slots.get("user_id")
            db: Session = next(get_db())
            if not user_id:
                # Resolver via número de destino (To) → User.whatsapp_number
                to_raw = slots.get("to")
                if to_raw:
                    user = db.query(User).filter(User.whatsapp_number == to_raw).first()
                    if user:
                        user_id = str(user.id)
                        slots["user_id"] = user_id
            if not user_id:
                return None
            # Se houver citação de serviço no texto, priorizar
            prioritized = await self._match_service_from_text(user_id, slots.get("text", ""), db)
            select_sql = "SELECT name, price, duration, description FROM services WHERE user_id = :uid AND is_active = 1 ORDER BY sort_order, name"
            services = db.execute(
                select_sql,
                {"uid": user_id},
            ).fetchall()
            if not services:
                return None
            parts = []
            ordered = services
            if prioritized:
                # mover o serviço citado para o topo
                # reconstruir prioritized com 4 colunas, consultando novamente se preciso
                if len(prioritized) == 3:
                    pr = db.execute(
                        "SELECT name, price, duration, description FROM services WHERE user_id = :uid AND name = :nm LIMIT 1",
                        {"uid": user_id, "nm": prioritized[0]},
                    ).fetchone()
                    prioritized_row = pr or (prioritized[0], prioritized[1], prioritized[2], None)
                else:
                    prioritized_row = prioritized
                ordered = [prioritized_row] + [r for r in services if r[0] != prioritized_row[0]]
            for row in ordered[:5]:
                name = row[0]
                price = row[1]
                duration = row[2]
                desc = row[3] if len(row) > 3 else None
                price_txt = f"R$ {float(price):.2f}" if price is not None else "sob consulta"
                if include_description and desc:
                    brief = self._truncate_description(desc)
                    parts.append(f"- {name}: {price_txt} ({duration}min) — {brief}")
                else:
                    parts.append(f"- {name}: {price_txt} ({duration}min)")
            header = "Meus serviços:\n"
            return header + "\n".join(parts)
        except Exception:
            return None

    async def _resolve_user_id(self, slots: Dict[str, Any], db: Session) -> Optional[str]:
        user_id = slots.get("user_id")
        if user_id:
            return user_id
        to_raw = slots.get("to")
        if to_raw:
            user = db.query(User).filter(User.whatsapp_number == to_raw).first()
            if user:
                slots["user_id"] = str(user.id)
                return str(user.id)
        return None

    async def _match_service_from_text(self, user_id: str, text: str, db: Session) -> Optional[tuple]:
        try:
            if not text:
                return None
            norm = normalize_and_correct(text)
            rows = db.execute(
                "SELECT name, price, duration FROM services WHERE user_id = :uid AND is_active = 1",
                {"uid": user_id},
            ).fetchall()
            if not rows:
                return None
            # Match direto por substring ou fuzzy
            best = None
            best_ratio = 0.0
            for r in rows:
                name = r[0]
                name_norm = normalize_and_correct(name)
                if name_norm and name_norm in norm:
                    return r
                ratio = difflib.SequenceMatcher(None, norm, name_norm).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best = r
            if best_ratio >= 0.6:
                return best
            return None
        except Exception:
            return None

    def _truncate_description(self, desc: Optional[str], limit: int = 120) -> str:
        if not desc:
            return ""
        d = desc.strip().replace("\n", " ")
        return d if len(d) <= limit else d[:limit].rstrip() + "..."

    async def _resolve_client_preferred_window(self, slots: Dict[str, Any]) -> Optional[str]:
        try:
            user_id = slots.get("user_id")
            client_whatsapp = slots.get("client_whatsapp") or slots.get("from")
            if not (user_id and client_whatsapp):
                return None
            db: Session = next(get_db())
            client = db.query(Client).filter(Client.user_id == user_id, Client.whatsapp == client_whatsapp).first()
            if not client or not client.preferred_times:
                return None
            # map strings livres para janela
            prefs = [p.lower() for p in client.preferred_times]
            if any("manh" in p for p in prefs):
                return "morning"
            if any("tarde" in p for p in prefs):
                return "afternoon"
            if any("noite" in p or "noit" in p for p in prefs):
                return "evening"
            return None
        except Exception:
            return None

    async def _try_create_appointment(self, slots: Dict[str, Any], tone: str) -> Optional[str]:
        try:
            user_id = slots.get("user_id")
            service_id = slots.get("service_id")
            date_iso = slots.get("date")
            time_str = slots.get("time")
            client_name = slots.get("client_name") or "Cliente WhatsApp"
            client_whatsapp = slots.get("client_whatsapp") or slots.get("from")

            if not (user_id and service_id and date_iso and time_str and client_whatsapp):
                return None

            # Montar datetime de início
            try:
                dt_date = datetime.fromisoformat(date_iso).date()
            except Exception:
                return None

            # Tentar parsear hora se veio no formato 10h/10:30
            t = parser.parse_time_from_text(time_str) or parser.parse_time_from_text(slots.get("text", ""))
            if not t:
                return None
            start_dt = datetime.combine(dt_date, t)

            # Criar agendamento público
            db: Session = next(get_db())
            plan_service = PlanService(db, None)
            appt_service = AppointmentService(db, plan_service)
            payload = PublicAppointmentCreate(
                service_id=service_id,
                client_name=client_name,
                client_whatsapp=client_whatsapp,
                client_email=None,
                start_time=start_dt,
                notes=None,
                source="bot",
            )
            appt = await appt_service.create_public_appointment(payload, user_id)

            # Mensagem de sucesso
            confirmed_time = f"{t.hour:02d}:{t.minute:02d}" if t.minute else f"{t.hour:02d}h"
            return templates.pick("confirm", tone, date=dt_date.strftime("%d/%m"), time=confirmed_time, service_name="o serviço") or "Agendamento criado com sucesso."

        except Exception:
            return None


