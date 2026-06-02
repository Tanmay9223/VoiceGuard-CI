"""
data/migrations/schema.py
SQLAlchemy table definitions (source of truth for Alembic migrations).
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, String, Text
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ScenarioRecord(Base):
    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    workflow = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    failure_class = Column(String, nullable=True)
    use_audio_pipeline = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CallResultRecord(Base):
    __tablename__ = "call_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False, index=True)
    scenario_id = Column(String, nullable=False, index=True)
    passed = Column(Boolean, nullable=False)
    failure_tags = Column(JSON, default=list)
    scores = Column(JSON, default=dict)
    transcript = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class EvalRunRecord(Base):
    __tablename__ = "eval_runs"

    run_id = Column(String, primary_key=True)
    trigger = Column(String, nullable=False)
    commit_sha = Column(String, nullable=False)
    release_decision = Column(String, nullable=False)
    total_scenarios = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    compliance_score = Column(Float, nullable=True)
    hallucination_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    tool_accuracy = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class FailureEventRecord(Base):
    __tablename__ = "failure_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False, index=True)
    scenario_id = Column(String, nullable=False)
    failure_tag = Column(String, nullable=False, index=True)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
