from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), nullable=False, default='📍')
    color = Column(String(7), nullable=False, default='#FF6B6B')
    is_active = Column(Boolean, default=True)

    places = relationship("Place", back_populates="category")


class Place(Base):
    __tablename__ = 'places'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(300))
    photo_url = Column(String(500))
    photo_source = Column(String(200))
    photo_author = Column(String(200))
    track_url = Column(String(500))
    track_author = Column(String(200))
    track_author_death_year = Column(Integer)
    track_title = Column(String(200))
    wifi_free = Column(Boolean, default=False)
    wheelchair_accessible = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    votes_count = Column(Integer, default=0)
    complaints_count = Column(Integer, default=0)
    is_reported = Column(Boolean, default=False)  # Добавлено поле!
    report_reason = Column(String(500))  # Добавлено поле!
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views_count = Column(Integer, default=0)

    category = relationship("Category", back_populates="places")
    votes = relationship("Vote", back_populates="place", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="place", cascade="all, delete-orphan")


class SuggestedPlace(Base):
    __tablename__ = 'suggested_places'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(Text, nullable=False)
    address = Column(String(300))
    latitude = Column(Float)
    longitude = Column(Float)
    suggester_name = Column(String(100))
    age_group = Column(String(50))
    photo_url = Column(String(500))
    photo_source = Column(String(200))
    photo_author = Column(String(200))
    track_url = Column(String(500))
    track_author = Column(String(200))
    track_author_death_year = Column(Integer)
    track_title = Column(String(200))
    wifi_free = Column(Boolean, default=False)
    wheelchair_accessible = Column(Boolean, default=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category")


class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(200))
    is_super_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey('places.id'), nullable=False)
    ip_address = Column(String(45), nullable=False)
    value = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    place = relationship("Place", back_populates="votes")

    __table_args__ = (
        Index('idx_unique_vote', 'place_id', 'ip_address', unique=True),
    )


class Complaint(Base):
    __tablename__ = 'complaints'

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey('places.id'), nullable=False)
    ip_address = Column(String(45), nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    place = relationship("Place", back_populates="complaints")

    __table_args__ = (
        Index('idx_unique_complaint', 'place_id', 'ip_address', unique=True),
    )