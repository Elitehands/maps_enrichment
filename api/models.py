from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey, BigInteger, Float
from geoalchemy2 import Geometry
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    locations = relationship("Location", back_populates="company")

class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str | None] = mapped_column(Text)
    plus_code: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    # Newly added enrichment fields
    duns_number: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)
    state_code: Mapped[str | None] = mapped_column(Text)
    county: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    features = relationship("Feature", back_populates="location", cascade="all, delete")
    company = relationship("Company", back_populates="locations")

class Feature(Base):
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    osm_id: Mapped[int | None] = mapped_column(BigInteger)
    osm_type: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    geometry = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326))
    bbox = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    data_source: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    location = relationship("Location", back_populates="features")
