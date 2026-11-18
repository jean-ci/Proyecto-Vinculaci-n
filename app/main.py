import json, os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pwdlib import PasswordHash
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from .database import Base, engine, get_db, SessionLocal
from . import models as m

APP_NAME=os.getenv('APP_NAME','Gestión de Proyectos UTA - MVP Fase 1')
SECRET_KEY=os.getenv('SECRET_KEY','development-only-change-me')
TOKEN_MINUTES=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES','480'))
ADMIN_EMAIL=os.getenv('BOOTSTRAP_ADMIN_EMAIL','admin@uta.edu.ec')
ADMIN_PASSWORD=os.getenv('BOOTSTRAP_ADMIN_PASSWORD','Admin12345!')
password_hash=PasswordHash.recommended()
app=FastAPI(title=APP_NAME, version='0.1.0', description='MVP - Fase 1')
app.mount('/static',StaticFiles(directory='app/static'),name='static')
templates=Jinja2Templates(directory='app/templates')
CATALOG=json.loads(Path('data/catalogs.json').read_text(encoding='utf-8'))

class LoginIn(BaseModel):
    email: EmailStr
    password: str
class ProjectIn(BaseModel):
    title: str=Field(min_length=3,max_length=300)
    activity_type_id: int
    responsible: str=Field(default='',max_length=180)
    career_id: int
    domain_id: int
    faculty_id: int
    line_id: int
    subline_id: int
    contribution_level_id: Optional[int]=None
    subject_ids: list[int]=[]
    outcome_ids: list[int]=[]
    evidence: str=''
    observations: str=''
class UserIn(BaseModel):
    full_name: str=Field(min_length=3,max_length=180)
    email: EmailStr
    password: str=Field(min_length=10)
    role_name: str
    career_id: Optional[int]=None

def token_for(user):
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id),'iat':now,'exp':now+timedelta(minutes=TOKEN_MINUTES)},SECRET_KEY,algorithm='HS256')
def current_user(request:Request, db:Session=Depends(get_db)):
    token=request.cookies.get('access_token')
    if not token: raise HTTPException(401,'Inicie sesión para continuar.')
    try: payload=jwt.decode(token,SECRET_KEY,algorithms=['HS256']); uid=int(payload['sub'])
    except Exception: raise HTTPException(401,'Sesión inválida o expirada.')
    user=db.get(m.User,uid)
    if not user or not user.active: raise HTTPException(401,'Usuario inactivo o inexistente.')
    return user
def require_roles(*roles):
    def dep(user:m.User=Depends(current_user)):
        if user.role.name not in roles: raise HTTPException(403,'No tiene permisos para esta operación.')
        return user
    return dep

def seed():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        roles=[('Administrador','Administración total del MVP'),('Coordinador de Carrera','Consulta de proyectos de su carrera'),('Coordinador de Vinculación','Consulta de proyectos de vinculación'),('Coordinador de Investigación','Consulta de investigación e innovación'),('Docente','Registro y edición de proyectos propios en borrador')]
        for name,desc in roles:
            if not db.scalar(select(m.Role).where(m.Role.name==name)): db.add(m.Role(name=name,description=desc))
        db.flush()
        for c in CATALOG['careers']:
            if not db.scalar(select(m.Career).where(m.Career.code==c['code'])): db.add(m.Career(code=c['code'],name=c['name']))
        db.flush()
        career_by_code={x.code:x for x in db.scalars(select(m.Career)).all()}
        for code,items in CATALOG['subjects'].items():
            career=career_by_code[code]
            for name in items:
                if not db.scalar(select(m.Subject).where(m.Subject.career_id==career.id,m.Subject.name==name)): db.add(m.Subject(career_id=career.id,name=name))
        for code,items in CATALOG['ra'].items():
            career=career_by_code[code]
            for item in items:
                if not db.scalar(select(m.LearningOutcome).where(m.LearningOutcome.career_id==career.id,m.LearningOutcome.code==item['code'])): db.add(m.LearningOutcome(career_id=career.id,code=item['code'],description=item['description']))
        for item in CATALOG['hierarchy']:
            domain=db.scalar(select(m.Domain).where(m.Domain.name==item['domain']))
            if not domain: domain=m.Domain(name=item['domain']); db.add(domain); db.flush()
            faculty=db.scalar(select(m.Faculty).where(m.Faculty.domain_id==domain.id,m.Faculty.name==item['faculty']))
            if not faculty: faculty=m.Faculty(domain_id=domain.id,name=item['faculty']); db.add(faculty); db.flush()
            line=db.scalar(select(m.ResearchLine).where(m.ResearchLine.faculty_id==faculty.id,m.ResearchLine.name==item['line']))
            if not line: line=m.ResearchLine(faculty_id=faculty.id,name=item['line']); db.add(line); db.flush()
            if not db.scalar(select(m.ResearchSubline).where(m.ResearchSubline.line_id==line.id,m.ResearchSubline.name==item['subline'])): db.add(m.ResearchSubline(line_id=line.id,name=item['subline']))
        for name in CATALOG['activity_types']:
            if not db.scalar(select(m.ActivityType).where(m.ActivityType.name==name)): db.add(m.ActivityType(name=name))
        db.flush()
        for typ,levels in CATALOG['scale'].items():
            at=db.scalar(select(m.ActivityType).where(m.ActivityType.name==typ))
            for level in levels:
                if not db.scalar(select(m.ContributionLevel).where(m.ContributionLevel.activity_type_id==at.id,m.ContributionLevel.level==level['level'])): db.add(m.ContributionLevel(activity_type_id=at.id,level=level['level'],label=level['label'],criterion=level['criterion']))
        db.flush()
        admin_role=db.scalar(select(m.Role).where(m.Role.name=='Administrador'))
        if not db.scalar(select(m.User).where(m.User.email==ADMIN_EMAIL)):
            db.add(m.User(full_name='Administrador del sistema',email=ADMIN_EMAIL,password_hash=password_hash.hash(ADMIN_PASSWORD),role_id=admin_role.id,active=True))
        db.commit()
    except: db.rollback(); raise
    finally: db.close()

@app.on_event('startup')
def startup(): seed()

@app.get('/',response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse('index.html',{'request':request,'app_name':APP_NAME})
@app.get('/health')
def health(): return {'status':'ok','phase':'Fase 1'}
@app.post('/api/auth/login')
def login(data:LoginIn,response:Response,db:Session=Depends(get_db)):
    user=db.scalar(select(m.User).options(joinedload(m.User.role),joinedload(m.User.career)).where(m.User.email==data.email))
    if not user or not user.active or not password_hash.verify(data.password,user.password_hash): raise HTTPException(401,'Correo o contraseña incorrectos.')
    response.set_cookie('access_token',token_for(user),httponly=True,samesite='lax',secure=False,max_age=TOKEN_MINUTES*60)
    return {'id':user.id,'full_name':user.full_name,'email':user.email,'role':user.role.name,'career':user.career.name if user.career else None}
@app.post('/api/auth/logout')
def logout(response:Response): response.delete_cookie('access_token'); return {'message':'Sesión cerrada'}
@app.get('/api/auth/me')
def me(user:m.User=Depends(current_user)):
    return {'id':user.id,'full_name':user.full_name,'email':user.email,'role':user.role.name,'career_id':user.career_id,'career':user.career.name if user.career else None}

@app.get('/api/catalogs')
def catalogs(user:m.User=Depends(current_user),db:Session=Depends(get_db)):
    def rows(cls,order): return [dict(id=x.id,**{k:getattr(x,k) for k in order}) for x in db.scalars(select(cls)).all()]
    return {
      'careers':rows(m.Career,['code','name']), 'activity_types':rows(m.ActivityType,['name']),
      'domains':rows(m.Domain,['name']), 'faculties':rows(m.Faculty,['domain_id','name']),
      'lines':rows(m.ResearchLine,['faculty_id','name']), 'sublines':rows(m.ResearchSubline,['line_id','name']),
      'subjects':rows(m.Subject,['career_id','name']), 'outcomes':rows(m.LearningOutcome,['career_id','code','description']),
      'levels':[dict(id=x.id,activity_type_id=x.activity_type_id,level=x.level,label=x.label,criterion=x.criterion) for x in db.scalars(select(m.ContributionLevel)).all()]
    }

def project_scope(stmt,user):
    if user.role.name=='Docente': return stmt.where(m.Project.created_by_id==user.id)
    if user.role.name=='Coordinador de Carrera': return stmt.where(m.Project.career_id==user.career_id)
    if user.role.name=='Coordinador de Vinculación': return stmt.join(m.ActivityType).where(m.ActivityType.name=='Vinculación')
    if user.role.name=='Coordinador de Investigación': return stmt.join(m.ActivityType).where(m.ActivityType.name.in_(['Investigación','Innovación']))
    return stmt

def project_dict(p):
    return {'id':p.id,'title':p.title,'activity_type':p.activity_type.name,'activity_type_id':p.activity_type_id,'responsible':p.responsible,'career':p.career.name,'career_id':p.career_id,'domain':p.domain_id,'faculty':p.faculty_id,'line':p.line_id,'subline':p.subline_id,'contribution_level_id':p.contribution_level_id,'subjects':[{'id':x.id,'name':x.name} for x in p.subjects],'outcomes':[{'id':x.id,'code':x.code,'description':x.description} for x in p.outcomes],'evidence':p.evidence,'observations':p.observations,'status':p.status,'created_at':p.created_at.isoformat(),'updated_at':p.updated_at.isoformat()}
@app.get('/api/projects')
def list_projects(user:m.User=Depends(current_user),db:Session=Depends(get_db)):
    stmt=project_scope(select(m.Project).options(joinedload(m.Project.activity_type),joinedload(m.Project.career),joinedload(m.Project.subjects),joinedload(m.Project.outcomes)),user)
    return [project_dict(p) for p in db.scalars(stmt.order_by(m.Project.updated_at.desc())).unique().all()]

def validate_project(data,db,user,existing=None):
    career=db.get(m.Career,data.career_id); at=db.get(m.ActivityType,data.activity_type_id)
    domain=db.get(m.Domain,data.domain_id); faculty=db.get(m.Faculty,data.faculty_id); line=db.get(m.ResearchLine,data.line_id); sub=db.get(m.ResearchSubline,data.subline_id)
    if not all([career,at,domain,faculty,line,sub]): raise HTTPException(422,'Uno o más elementos de catálogo no existen.')
    if user.role.name=='Docente' and user.career_id and user.career_id!=career.id: raise HTTPException(403,'Solo puede registrar proyectos de su carrera.')
    if faculty.domain_id!=domain.id or line.faculty_id!=faculty.id or sub.line_id!=line.id: raise HTTPException(422,'La selección de dominio, facultad, línea y sublínea no corresponde.')
    subjects=db.scalars(select(m.Subject).where(m.Subject.id.in_(data.subject_ids),m.Subject.career_id==career.id)).all() if data.subject_ids else []
    outcomes=db.scalars(select(m.LearningOutcome).where(m.LearningOutcome.id.in_(data.outcome_ids),m.LearningOutcome.career_id==career.id)).all() if data.outcome_ids else []
    if len(subjects)!=len(set(data.subject_ids)) or len(outcomes)!=len(set(data.outcome_ids)): raise HTTPException(422,'Las asignaturas y RA deben pertenecer a la carrera seleccionada.')
    if data.contribution_level_id:
        level=db.get(m.ContributionLevel,data.contribution_level_id)
        if not level or level.activity_type_id!=at.id: raise HTTPException(422,'El nivel de contribución no corresponde al tipo de actividad.')
    return career,at,subjects,outcomes
@app.post('/api/projects')
def create_project(data:ProjectIn,user:m.User=Depends(require_roles('Docente','Administrador')),db:Session=Depends(get_db)):
    career,at,subjects,outcomes=validate_project(data,db,user)
    p=m.Project(title=data.title,activity_type_id=at.id,responsible=data.responsible,career_id=career.id,domain_id=data.domain_id,faculty_id=data.faculty_id,line_id=data.line_id,subline_id=data.subline_id,contribution_level_id=data.contribution_level_id,evidence=data.evidence,observations=data.observations,status='Borrador',created_by_id=user.id,subjects=subjects,outcomes=outcomes)
    db.add(p); db.commit(); db.refresh(p)
    return project_dict(db.scalars(select(m.Project).options(joinedload(m.Project.activity_type),joinedload(m.Project.career),joinedload(m.Project.subjects),joinedload(m.Project.outcomes)).where(m.Project.id==p.id)).unique().one())
@app.put('/api/projects/{project_id}')
def update_project(project_id:int,data:ProjectIn,user:m.User=Depends(require_roles('Docente','Administrador')),db:Session=Depends(get_db)):
    p=db.get(m.Project,project_id)
    if not p: raise HTTPException(404,'Proyecto no encontrado.')
    if user.role.name!='Administrador' and (p.created_by_id!=user.id or p.status!='Borrador'): raise HTTPException(403,'Solo puede editar sus propios borradores.')
    career,at,subjects,outcomes=validate_project(data,db,user,p)
    for k in ['title','responsible','domain_id','faculty_id','line_id','subline_id','contribution_level_id','evidence','observations']: setattr(p,k,getattr(data,k))
    p.career_id=career.id; p.activity_type_id=at.id; p.subjects=subjects; p.outcomes=outcomes
    db.commit(); db.refresh(p)
    p=db.scalars(select(m.Project).options(joinedload(m.Project.activity_type),joinedload(m.Project.career),joinedload(m.Project.subjects),joinedload(m.Project.outcomes)).where(m.Project.id==p.id)).unique().one()
    return project_dict(p)
@app.delete('/api/projects/{project_id}')
def delete_project(project_id:int,user:m.User=Depends(require_roles('Docente','Administrador')),db:Session=Depends(get_db)):
    p=db.get(m.Project,project_id)
    if not p: raise HTTPException(404,'Proyecto no encontrado.')
    if user.role.name!='Administrador' and (p.created_by_id!=user.id or p.status!='Borrador'): raise HTTPException(403,'Solo puede eliminar sus propios borradores.')
    db.delete(p); db.commit(); return {'message':'Borrador eliminado'}
@app.post('/api/users')
def create_user(data:UserIn,user:m.User=Depends(require_roles('Administrador')),db:Session=Depends(get_db)):
    role=db.scalar(select(m.Role).where(m.Role.name==data.role_name)); career=db.get(m.Career,data.career_id) if data.career_id else None
    if not role: raise HTTPException(422,'Rol no válido.')
    if db.scalar(select(m.User).where(m.User.email==data.email)): raise HTTPException(409,'El correo ya está registrado.')
    if data.role_name in ['Docente','Coordinador de Carrera'] and not career: raise HTTPException(422,'Este rol requiere una carrera asignada.')
    obj=m.User(full_name=data.full_name,email=data.email,password_hash=password_hash.hash(data.password),role_id=role.id,career_id=career.id if career else None)
    db.add(obj); db.commit(); return {'message':'Usuario creado','id':obj.id}
@app.get('/api/users')
def list_users(user:m.User=Depends(require_roles('Administrador')),db:Session=Depends(get_db)):
    items=db.scalars(select(m.User).options(joinedload(m.User.role),joinedload(m.User.career)).order_by(m.User.full_name)).all()
    return [{'id':x.id,'full_name':x.full_name,'email':x.email,'role':x.role.name,'career':x.career.name if x.career else None,'active':x.active} for x in items]
