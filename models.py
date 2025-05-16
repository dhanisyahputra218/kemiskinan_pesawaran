from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create database engine
engine = create_engine('sqlite:///kemiskinan.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

class KemiskinanData(Base):
    __tablename__ = 'kemiskinan_data'

    id = Column(Integer, primary_key=True)
    kabupaten = Column(String)
    kecamatan = Column(String)
    desa = Column(String)
    tahun = Column(Integer)
    jum_penduduk = Column(Float)
    persentase_pen_miskin = Column(Float)
    jumlah_pen_miskin = Column(Float)
    garis_kemiskinan = Column(Float)
    persentase_ruta_miskin_bpnt = Column(Float)
    jumlah_kg_bulan = Column(Float)
    harga_kg = Column(Float)
    sanitasi_layak = Column(String)
    air_minum_layak = Column(String)
    rata_pendapatan_hari = Column(Float)
    total_pendapatan_bulan = Column(Float)
    total_pengeluaran_bulan = Column(Float)
    pengeluaran_hari = Column(Float)
    miskin = Column(Float)
    tidak_miskin = Column(Float)
    miskin_tidak_miskin = Column(Float)
    bekerja_pertanian = Column(Float)
    bekerja_non_pertanian = Column(Float)
    mencari_pekerjaan = Column(Float)
    tidak_bekerja = Column(Float)
    persentase_pengangguran = Column(Float)
    tingkat_kekumuhan = Column(String)
    luas_kumuh = Column(Float)
    pendidikan_sd = Column(Float)
    pendidikan_smp = Column(Float)
    pendidikan_sma = Column(Float)
    ipm = Column(Float)

# Create all tables
Base.metadata.create_all(engine)
