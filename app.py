from flask import Flask, jsonify, request, render_template, send_from_directory, redirect, url_for, flash
from flask_cors import CORS
from datetime import datetime
import json
import os
import pandas as pd
import numpy as np
from models import Session, KemiskinanData

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Global variable for dataset
df = None

# Configure static and template folders
app.static_folder = 'static'
app.static_url_path = '/static'
app.template_folder = 'templates'

# Error handler for 500 errors
@app.errorhandler(500)
def handle_500_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error)
    }), 500

# Error handler for 404 errors
@app.errorhandler(404)
def handle_404_error(error):
    return jsonify({
        'error': 'Not Found',
        'message': str(error)
    }), 404

# Route for root URL
@app.route('/')
def index():
    return render_template('index.html')

# Load and preprocess dataset
def load_dataset():
    try:
        # First try to read the CSV file
        try:
            df = pd.read_csv('static/data/Dataset kemiskinan - pesawaran.csv', 
                           skipinitialspace=True,      # Skip spaces after delimiter
                           skip_blank_lines=True,      # Skip empty lines
                           on_bad_lines='warn')        # Warn about bad lines instead of failing
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}\nAttempting to clean the file...")
            
            # If regular read fails, try to clean the file first
            with open('static/data/Dataset kemiskinan - pesawaran.csv', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Remove empty lines and clean the data
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            
            # Write cleaned data back
            with open('static/data/Dataset kemiskinan - pesawaran.csv', 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            
            # Try reading again
            df = pd.read_csv('static/data/Dataset kemiskinan - pesawaran.csv',
                           skipinitialspace=True,
                           skip_blank_lines=True,
                           on_bad_lines='warn')
        
        if len(df) == 0:
            raise Exception("Dataset is empty after loading")
            
        # Clean up column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('(', '').str.replace(')', '')
        
        # Convert currency columns
        currency_columns = [
            'garis_kemiskinanrp/kap/bulan',
            'harga_rp/kg',
            'rata-rata_pendapatan/hari',
            'total_pendapatan/bulan',
            'total_pengeluaran/bulan',
            'pengeluaran/hari'
        ]
        
        for col in currency_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('Rp', '').str.replace('.', '').str.replace(',', '').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert percentage columns
        percentage_columns = [
            'persentase_pen_miskin',
            'persentase_pengangguran',
            'persentase_ruta_miskin_penerima_bpnt/program_sembako',
            'ipmindeks_pembangunan_manusia'
        ]
        
        for col in percentage_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip('"')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"Successfully loaded dataset with {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error loading dataset: {str(e)}\nPlease check if the CSV file is properly formatted")
        return None

df = load_dataset()

# Kecamatan coordinates (approximate)
KECAMATAN_COORDS = {
    'Gedong Tataan': {'lat': -5.3981, 'lng': 105.2524},
    'Kedondong': {'lat': -5.3827, 'lng': 105.1724},
    'Negeri Katon': {'lat': -5.3167, 'lng': 105.1333},
    'Padang Cermin': {'lat': -5.5833, 'lng': 105.2167},
    'Punduh Pidada': {'lat': -5.7000, 'lng': 105.2000},
    'Tegineneng': {'lat': -5.2833, 'lng': 105.3167},
    'Way Khilau': {'lat': -5.4667, 'lng': 105.1333},
    'Way Lima': {'lat': -5.4500, 'lng': 105.1000},
    'Way Ratai': {'lat': -5.5000, 'lng': 105.1833},
    'Teluk Pandan': {'lat': -5.6333, 'lng': 105.2333},
    'Marga Punduh': {'lat': -5.6500, 'lng': 105.1833}
}

def get_filtered_data():
    filtered_df = df.copy()
    
    year = request.args.get('year')
    kecamatan = request.args.get('kecamatan')
    desa = request.args.get('desa')
    
    print(f"\nDebug - Filter parameters:")
    print(f"Year: {year}")
    print(f"Kecamatan ID: {kecamatan}")
    print(f"Desa: {desa}")
    
    try:
        if year:
            filtered_df = filtered_df[filtered_df['tahun'] == int(year)]
            print(f"After year filter: {len(filtered_df)} rows")
        
        if kecamatan:
            # Get kecamatan name from ID
            kecamatan_map = {
                str(i+1): kec
                for i, kec in enumerate(sorted(df['kecamatan'].unique()))
            }
            kec_name = kecamatan_map.get(kecamatan)
            print(f"Kecamatan name for ID {kecamatan}: {kec_name}")
            
            if kec_name:
                filtered_df = filtered_df[filtered_df['kecamatan'].str.lower() == kec_name.lower()]
                print(f"After kecamatan filter: {len(filtered_df)} rows")
        
        if desa:
            filtered_df = filtered_df[filtered_df['desa'].str.lower() == desa.lower()]
            print(f"After desa filter: {len(filtered_df)} rows")
        
        if filtered_df.empty:
            print("Warning: No data matches the current filters")
        else:
            print("\nDebug - Sample of filtered data:")
            print(filtered_df[['tahun', 'kecamatan', 'desa', 'total_pendapatan/bulan', 'total_pengeluaran/bulan', 'harga_rp/kg', 'persentase_pengangguran', 'persentase_pen_miskin']].head())
            
    except Exception as e:
        print(f"Error filtering data: {str(e)}")
    
    return filtered_df

@app.route('/api/statistics')
def get_statistics():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify({
                'total_pendapatan': 0,
                'total_pengeluaran': 0,
                'bpk_umkm': 0,
                'persentase_pengangguran': 0,
                'persentase_kemiskinan': 0
            })
        
        # Calculate statistics based on filtered data
        stats = {
            'total_pendapatan': float(filtered_df['total_pendapatan/bulan'].mean()),
            'total_pengeluaran': float(filtered_df['total_pengeluaran/bulan'].mean()),
            'bpk_umkm': float(filtered_df['harga_rp/kg'].mean()),
            'persentase_pengangguran': float(filtered_df['persentase_pengangguran'].mean()),
            'persentase_kemiskinan': float(filtered_df['persentase_pen_miskin'].mean())
        }
        
        print("\nDebug - Calculated statistics:")
        print(stats)
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/map-data')
def get_map_data():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify([])

        map_data = []
        
        for _, row in filtered_df.iterrows():
            try:
                # Get data for this kecamatan
                total_population = float(row['jum_penduduk']) * 1000  # Convert from thousands to actual number
                poor_population = float(row['jumlah_pen_miskin'])
                poverty_percentage = float(row['persentase_pen_miskin'])
                unemployment = float(row['persentase_pengangguran'])
                ipm = float(row['ipmindeks_pembangunan_manusia'])
                
                map_data.append({
                    'kecamatan': row['kecamatan'],
                    'total_population': total_population,
                    'poor_population': poor_population,
                    'poverty_percentage': poverty_percentage,
                    'pengangguran': unemployment,
                    'ipm': ipm
                })
                
            except Exception as e:
                print(f"Error processing row for kecamatan {row.get('kecamatan', 'unknown')}: {str(e)}")
                continue
        
        print("\nDebug - Map data sample:")
        if map_data:
            print(map_data[0])
        
        return jsonify(map_data)
        
    except Exception as e:
        print(f"Error in get_map_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/poverty-distribution')
def get_poverty_distribution():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify({'labels': [], 'data': []})
        
        # Group by kecamatan and calculate poor population
        poverty_data = filtered_df.groupby('kecamatan')['jumlah_pen_miskin'].sum().sort_values(ascending=False)
        
        return jsonify({
            'labels': poverty_data.index.tolist(),
            'data': poverty_data.values.tolist()
        })
    except Exception as e:
        print(f"Error in get_poverty_distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/poverty-trend')
def get_poverty_trend():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify({'labels': [], 'data': []})
        
        # Group by year and calculate average poverty rate
        trend_data = filtered_df.groupby('tahun')['persentase_pen_miskin'].mean()
        
        return jsonify({
            'labels': trend_data.index.tolist(),
            'data': trend_data.values.tolist()
        })
    except Exception as e:
        print(f"Error in get_poverty_trend: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/income-expense')
def get_income_expense():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify({'labels': [], 'income': [], 'expense': []})
        
        # Group by kecamatan
        data = filtered_df.groupby('kecamatan').agg({
            'total_pendapatan/bulan': 'mean',
            'total_pengeluaran/bulan': 'mean'
        }).round(2)
        
        return jsonify({
            'labels': data.index.tolist(),
            'income': data['total_pendapatan/bulan'].tolist(),
            'expense': data['total_pengeluaran/bulan'].tolist()
        })
    except Exception as e:
        print(f"Error in get_income_expense: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ipm')
def get_ipm():
    try:
        filtered_df = get_filtered_data()
        if filtered_df.empty:
            return jsonify({'labels': [], 'data': []})
        
        # Calculate IPM components
        ipm_data = {
            'labels': ['Pendidikan', 'Kesehatan', 'Ekonomi', 'Infrastruktur', 'Sosial'],
            'data': [
                float(filtered_df['ipmindeks_pembangunan_manusia'].mean()),
                70.0,  # Default value for health
                float((filtered_df['total_pendapatan/bulan'].mean() / filtered_df['jum_penduduk'].mean()) / 1000000),
                70.0,  # Default value for infrastructure
                float(filtered_df['persentase_pen_miskin'].mean())
            ]
        }
        
        return jsonify(ipm_data)
    except Exception as e:
        print(f"Error in get_ipm: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/filters')
def get_filters():
    try:
        # Get unique years
        years = sorted(df['tahun'].unique().tolist())
        
        # Get unique kecamatan with IDs
        kecamatans = [
            {'id': str(i+1), 'nama': kec}
            for i, kec in enumerate(sorted(df['kecamatan'].unique()))
        ]
        
        return jsonify({
            'tahun': years,
            'kecamatan': kecamatans
        })
    except Exception as e:
        print(f"Error in get_filters: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/desa/<kecamatan_id>')
def get_desa(kecamatan_id):
    try:
        # Map kecamatan_id to kecamatan name
        kecamatan_map = {
            str(i+1): kec
            for i, kec in enumerate(sorted(df['kecamatan'].unique()))
        }
        
        kecamatan = kecamatan_map.get(kecamatan_id)
        if not kecamatan:
            return jsonify([]), 404
        
        # Get desa list for the kecamatan
        desa_list = sorted(df[df['kecamatan'] == kecamatan]['desa'].unique().tolist())
        return jsonify(desa_list)
    except Exception as e:
        print(f"Error in get_desa: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/kecamatan')
def get_kecamatan():
    try:
        kecamatan = sorted(df['kecamatan'].unique().tolist())
        return jsonify(kecamatan)
    except Exception as e:
        print(f"Error in get_kecamatan: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/desa')
def get_desa_by_kecamatan():
    try:
        kecamatan = request.args.get('kecamatan')
        if kecamatan:
            # Get kecamatan name from ID
            kecamatan_map = {
                str(i+1): kec
                for i, kec in enumerate(sorted(df['kecamatan'].unique()))
            }
            kec_name = kecamatan_map.get(kecamatan)
            if kec_name:
                desa = sorted(df[df['kecamatan'] == kec_name]['desa'].unique().tolist())
                return jsonify(desa)
        
        return jsonify([])
    except Exception as e:
        print(f"Error in get_desa: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/input', methods=['GET'])
def input_form():
    return render_template('input.html')

@app.route('/submit-data', methods=['POST'])
def submit_data():
    try:
        # Create database session
        session = Session()

        # Create new database record
        new_record = KemiskinanData(
            kabupaten='Pesawaran',  # Default value
            kecamatan=request.form.get('kecamatan'),
            desa=request.form.get('desa'),
            tahun=int(request.form.get('tahun')),
            jum_penduduk=float(request.form.get('jum_penduduk')),
            persentase_pen_miskin=float(request.form.get('persentase_pen_miskin')),
            jumlah_pen_miskin=float(request.form.get('jum_penduduk')) * float(request.form.get('persentase_pen_miskin')) / 100,
            garis_kemiskinan=float(request.form.get('garis_kemiskinan', 0)),
            persentase_ruta_miskin_bpnt=float(request.form.get('persentase_ruta_miskin_bpnt', 0)),
            jumlah_kg_bulan=float(request.form.get('jumlah_kg_bulan', 0)),
            harga_kg=float(request.form.get('harga_kg', 0)),
            sanitasi_layak=request.form.get('sanitasi_layak', 'Layak'),
            air_minum_layak=request.form.get('air_minum_layak', 'Layak'),
            rata_pendapatan_hari=float(request.form.get('rata_pendapatan_hari', 0)),
            total_pendapatan_bulan=float(request.form.get('total_pendapatan')),
            total_pengeluaran_bulan=float(request.form.get('total_pengeluaran')),
            pengeluaran_hari=float(request.form.get('total_pengeluaran')) / 30,  # Approximate
            miskin=float(request.form.get('miskin', 0)),
            tidak_miskin=float(request.form.get('tidak_miskin', 0)),
            miskin_tidak_miskin=float(request.form.get('miskin_tidak_miskin', 0)),
            bekerja_pertanian=float(request.form.get('bekerja_pertanian', 0)),
            bekerja_non_pertanian=float(request.form.get('bekerja_non_pertanian', 0)),
            mencari_pekerjaan=float(request.form.get('mencari_pekerjaan', 0)),
            tidak_bekerja=float(request.form.get('tidak_bekerja', 0)),
            persentase_pengangguran=float(request.form.get('persentase_pengangguran')),
            tingkat_kekumuhan=request.form.get('tingkat_kekumuhan', 'Kumuh Sedang'),
            luas_kumuh=float(request.form.get('luas_kumuh', 0)),
            pendidikan_sd=float(request.form.get('pendidikan_sd', 0)),
            pendidikan_smp=float(request.form.get('pendidikan_smp', 0)),
            pendidikan_sma=float(request.form.get('pendidikan_sma', 0)),
            ipm=float(request.form.get('ipm', 0))
        )

        # Add to database
        session.add(new_record)
        session.commit()

        # Prepare data for CSV
        data = {
            'Kabupaten': 'Pesawaran',
            'Kecamatan': request.form.get('kecamatan'),
            'Desa': request.form.get('desa'),
            'Tahun': request.form.get('tahun'),
            'Jum Penduduk': request.form.get('jum_penduduk'),
            'Persentase Pen Miskin': request.form.get('persentase_pen_miskin'),
            'Jumlah Pen Miskin': float(request.form.get('jum_penduduk')) * float(request.form.get('persentase_pen_miskin')) / 100,
            'Garis Kemiskinan(Rp/Kap/Bulan)': f"Rp{request.form.get('garis_kemiskinan', '0')},00",
            'Persentase Ruta Miskin Penerima BPNT/Program Sembako (%)': request.form.get('persentase_ruta_miskin_bpnt', '0'),
            'Jumlah (kg/ bulan)': request.form.get('jumlah_kg_bulan', '0'),
            'Harga (Rp/Kg)': f"Rp{request.form.get('harga_kg', '0')}",
            'Persentase Rumah Tangga Memiliki Akses Sanitasi Layak': request.form.get('sanitasi_layak', 'Layak'),
            'Persentasi Rumah Tangga Memiliki Akses Air Minum Layak ': request.form.get('air_minum_layak', 'Layak'),
            'Rata-rata pendapatan/hari': f"Rp{request.form.get('rata_pendapatan_hari', '0')}",
            'Total pendapatan/bulan': request.form.get('total_pendapatan'),
            'Total pengeluaran/bulan': f"Rp{request.form.get('total_pengeluaran')}",
            'Pengeluaran/hari': f"Rp{float(request.form.get('total_pengeluaran')) / 30:.0f}",
            'Miskin': request.form.get('miskin', '0'),
            'Tidak Miskin': request.form.get('tidak_miskin', '0'),
            'Miskin dan Tidak Miskin': request.form.get('miskin_tidak_miskin', '0'),
            'Bekerja di sektor pertanian': request.form.get('bekerja_pertanian', '0'),
            'Bekerja bukan di sektor pertanian': request.form.get('bekerja_non_pertanian', '0'),
            'Mencari pekerjaan': request.form.get('mencari_pekerjaan', '0'),
            'Tidak bekerja': request.form.get('tidak_bekerja', '0'),
            'Persentase Pengangguran': request.form.get('persentase_pengangguran'),
            'Tingkat Kekumuhan': request.form.get('tingkat_kekumuhan', 'Kumuh Sedang'),
            'Luas Kumuh (Ha)': request.form.get('luas_kumuh', '0'),
            '<SD': request.form.get('pendidikan_sd', '0'),
            'Tamat SD/SMP': request.form.get('pendidikan_smp', '0'),
            '>SMA': request.form.get('pendidikan_sma', '0'),
            'IPM(indeks pembangunan manusia)': request.form.get('ipm', '0')
        }
        
        # Create new dataframe with the data
        new_df = pd.DataFrame([data])
        
        # Load and update CSV
        csv_path = 'static/data/Dataset kemiskinan - pesawaran.csv'
        current_df = pd.read_csv(csv_path)
        current_df = pd.concat([current_df, new_df], ignore_index=True)
        current_df.to_csv(csv_path, index=False)
        
        # Update the global dataset
        global df
        df = current_df.copy()
        
        session.close()
        flash('Data berhasil disimpan ke database dan CSV!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('input_form'))

if __name__ == '__main__':
    if df is None:
        print("Error: Could not load dataset. Please check the file and its format.")
    else:
        try:
            print('Starting Flask server...')
            app.run(debug=True, host='0.0.0.0', port=5000)
        except Exception as e:
            print(f'Error starting server: {e}')
