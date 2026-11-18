from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Table, Column, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

project_subjects = Table('project_subjects', Base.metadata,
    Column('project_id', ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('subject_id', ForeignKey('subjects.id'), primary_key=True))
project_outcomes = Table('project_outcomes', Base.metadata,
    Column('project_id', ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('outcome_id', ForeignKey('learning_outcomes.id'), primary_key=True))

class Role(Base):
    __tablename__='roles'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(50), unique=True)
    description: Mapped[str]=mapped_column(String(180), default='')

class Career(Base):
    __tablename__='careers'
    id: Mapped[int]=mapped_column(primary_key=True)
    code: Mapped[str]=mapped_column(String(10), unique=True)
    name: Mapped[str]=mapped_column(String(180), unique=True)

class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    full_name: Mapped[str]=mapped_column(String(180))
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    role_id: Mapped[int]=mapped_column(ForeignKey('roles.id'))
    career_id: Mapped[int|None]=mapped_column(ForeignKey('careers.id'), nullable=True)
    role: Mapped[Role]=relationship()
    career: Mapped[Career|None]=relationship()

class Subject(Base):
    __tablename__='subjects'
    id: Mapped[int]=mapped_column(primary_key=True)
    career_id: Mapped[int]=mapped_column(ForeignKey('careers.id'))
    name: Mapped[str]=mapped_column(String(220))
    __table_args__=(UniqueConstraint('career_id','name'),)

class LearningOutcome(Base):
    __tablename__='learning_outcomes'
    id: Mapped[int]=mapped_column(primary_key=True)
    career_id: Mapped[int]=mapped_column(ForeignKey('careers.id'))
    code: Mapped[str]=mapped_column(String(20))
    description: Mapped[str]=mapped_column(Text)
    __table_args__=(UniqueConstraint('career_id','code'),)

class Domain(Base):
    __tablename__='domains'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(220), unique=True)

class Faculty(Base):
    __tablename__='faculties'
    id: Mapped[int]=mapped_column(primary_key=True)
    domain_id: Mapped[int]=mapped_column(ForeignKey('domains.id'))
    name: Mapped[str]=mapped_column(String(220))
    __table_args__=(UniqueConstraint('domain_id','name'),)

class ResearchLine(Base):
    __tablename__='research_lines'
    id: Mapped[int]=mapped_column(primary_key=True)
    faculty_id: Mapped[int]=mapped_column(ForeignKey('faculties.id'))
    name: Mapped[str]=mapped_column(String(250))
    __table_args__=(UniqueConstraint('faculty_id','name'),)

class ResearchSubline(Base):
    __tablename__='research_sublines'
    id: Mapped[int]=mapped_column(primary_key=True)
    line_id: Mapped[int]=mapped_column(ForeignKey('research_lines.id'))
    name: Mapped[str]=mapped_column(String(300))
    __table_args__=(UniqueConstraint('line_id','name'),)

class ActivityType(Base):
    __tablename__='activity_types'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(50), unique=True)

class ContributionLevel(Base):
    __tablename__='contribution_levels'
    id: Mapped[int]=mapped_column(primary_key=True)
    activity_type_id: Mapped[int]=mapped_column(ForeignKey('activity_types.id'))
    level: Mapped[int]=mapped_column(Integer)
    label: Mapped[str]=mapped_column(String(80))
    criterion: Mapped[str]=mapped_column(Text)
    __table_args__=(UniqueConstraint('activity_type_id','level'),)

class Project(Base):
    __tablename__='projects'
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(300), index=True)
    activity_type_id: Mapped[int]=mapped_column(ForeignKey('activity_types.id'))
    responsible: Mapped[str]=mapped_column(String(180), default='')
    career_id: Mapped[int]=mapped_column(ForeignKey('careers.id'), index=True)
    domain_id: Mapped[int]=mapped_column(ForeignKey('domains.id'))
    faculty_id: Mapped[int]=mapped_column(ForeignKey('faculties.id'))
    line_id: Mapped[int]=mapped_column(ForeignKey('research_lines.id'))
    subline_id: Mapped[int]=mapped_column(ForeignKey('research_sublines.id'))
    contribution_level_id: Mapped[int|None]=mapped_column(ForeignKey('contribution_levels.id'), nullable=True)
    evidence: Mapped[str]=mapped_column(Text, default='')
    observations: Mapped[str]=mapped_column(Text, default='')
    status: Mapped[str]=mapped_column(String(30), default='Borrador', index=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    subjects: Mapped[list[Subject]]=relationship(secondary=project_subjects)
    outcomes: Mapped[list[LearningOutcome]]=relationship(secondary=project_outcomes)
    activity_type: Mapped[ActivityType]=relationship()
    career: Mapped[Career]=relationship()
    creator: Mapped[User]=relationship()
