import sys
sys.path.insert(0, '/opt/smart-crm-bot')
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from database import async_session, init_db
from models import Contact, User
from webapp.auth import authenticate
from datetime import datetime, timezone

app = FastAPI(title="Smart CRM Panel")
templates = Jinja2Templates(directory="/opt/smart-crm-bot/webapp/templates")

@app.on_event("startup")
async def startup():
    await init_db()

# Главная страница (список контактов)
@app.get("/", response_class=HTMLResponse)
async def list_contacts(request: Request, search: str = "", username: str = Depends(authenticate)):
    async with async_session() as session:
        user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
            return HTMLResponse("Нет пользователей в базе. Сначала запустите бота и выполните /start.")
        query = select(Contact).where(Contact.owner_id == user.id)
        if search:
            query = query.where(
                Contact.name.ilike(f"%{search}%") |
                Contact.sphere.ilike(f"%{search}%") |
                Contact.tags.ilike(f"%{search}%")
            )
        contacts = (await session.execute(query.order_by(Contact.created_at.desc()))).scalars().all()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "contacts": contacts,
            "search": search,
            "username": username,
            "now": datetime.now(timezone.utc)
        })

# Аналитика (заглушка с базовой статистикой)
@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request, username: str = Depends(authenticate)):
    async with async_session() as session:
        user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
            return HTMLResponse("Нет данных.")
        sphere_counts = (await session.execute(
            select(Contact.sphere, func.count(Contact.id))
            .where(Contact.owner_id == user.id)
            .group_by(Contact.sphere)
        )).all()
        contacts = (await session.execute(
            select(Contact).where(Contact.owner_id == user.id)
        )).scalars().all()
        now = datetime.now(timezone.utc)
        top_forgotten = []
        for c in contacts:
            if c.last_contacted_at:
                delta = (now - c.last_contacted_at.replace(tzinfo=timezone.utc)).days
            else:
                delta = 9999
            top_forgotten.append((c.name, delta))
        top_forgotten.sort(key=lambda x: x[1], reverse=True)
        top_forgotten = top_forgotten[:10]
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "username": username,
            "sphere_counts": sphere_counts,
            "top_forgotten": top_forgotten
        })

# Редактирование контакта
@app.get("/edit/{contact_id}", response_class=HTMLResponse)
async def edit_contact_form(contact_id: int, request: Request, username: str = Depends(authenticate)):
    async with async_session() as session:
        contact = await session.get(Contact, contact_id)
        if not contact:
            return HTMLResponse("Контакт не найден", status_code=404)
        return templates.TemplateResponse("edit_contact.html", {
            "request": request,
            "contact": contact,
            "username": username
        })

@app.post("/edit/{contact_id}")
async def save_contact(contact_id: int, sphere: str = Form(""), tags: str = Form(""),
                       username: str = Depends(authenticate)):
    async with async_session() as session:
        contact = await session.get(Contact, contact_id)
        if contact:
            contact.sphere = sphere
            contact.tags = tags
            await session.commit()
    return RedirectResponse(f"/edit/{contact_id}", status_code=303)
