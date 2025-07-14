import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

# Konfigurasi halaman
st.set_page_config(page_title="Cuaca Sabu Raijua", layout="wide")

# Header Aplikasi
st.title("📍 Prakiraan Cuaca Wilayah Kabupaten Sabu Raijua")
st.subheader("Semuel Radja Uli_M8TB_14.24.0011")
st.caption("Visualisasi Realtime dari Model GFS via NOAA/NOMADS")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Sidebar
st.sidebar.title("⚙️ Pengaturan Visualisasi")

# Input pengguna
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam Prediksi ke Depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Pilih Parameter Cuaca", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

# Tombol untuk visualisasi
if st.sidebar.button("🔍 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("Dataset berhasil dimuat dari server NOAA.")
    except Exception as e:
        st.error(f"Gagal memuat data GFS: {e}")
        st.stop()

    is_contour = False
    is_vector = False

    # Penyesuaian parameter dan warna
    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
        vmin, vmax = 0, 50
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu (°C)"
        cmap = "coolwarm"
        vmin, vmax = -5, 35
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = plt.cm.get_cmap("RdYlGn_r", 10)
        vmin, vmax = 0, 30
        is_vector = True
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        vmin, vmax = 990, 1025
        is_contour = True
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Filter wilayah SABU RAIJUA: zoom lokal
    lat_min, lat_max = -11.0, -10.0
    lon_min, lon_max = 121.5, 122.3
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Plotting peta
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # Waktu validasi
    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    # Plot data
    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15,
                        colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            ax.quiver(var.lon[::2], var.lat[::2],
                      u.values[::2, ::2], v.values[::2, ::2],
                      transform=ccrs.PlateCarree(), scale=500,
                      width=0.002, color='black')

    # Marker lokasi Sabu Raijua
    sabu_lat, sabu_lon = -10.525, 121.85
    ax.plot(sabu_lon, sabu_lat, marker='o', color='red', markersize=6,
            transform=ccrs.PlateCarree(), label='Sabu Raijua')
    ax.text(sabu_lon + 0.05, sabu_lat, "Sabu Raijua", fontsize=8, color='red',
            transform=ccrs.PlateCarree())

    # Fitur peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

    # Tampilkan peta
    st.pyplot(fig)
