import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="글로벌 지진 시각화 대시보드", page_icon="🌍", layout="wide")

st.title("🌍 전 세계 연도별 지진 시각화 앱")
st.markdown("USGS(미국 지질조사국) API를 활용하여 선택한 연도의 규모 5.0 이상 지진 데이터를 시각화합니다.")

# USGS API에서 데이터를 가져오는 함수 (캐싱 적용하여 속도 향상)
@st.cache_data(ttl=86400) # 24시간 동안 데이터 캐싱
def fetch_earthquake_data(year):
    # API 요청 파라미터 설정 (규모 5.0 이상으로 제한하여 데이터 과부하 방지)
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": f"{year}-01-01",
        "endtime": f"{year}-12-31",
        "minmagnitude": 5.0, 
        "limit": 20000
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # GeoJSON 데이터에서 필요한 정보만 추출하여 DataFrame으로 변환
        features = data.get("features", [])
        parsed_data = []
        for feature in features:
            properties = feature["properties"]
            geometry = feature["geometry"]
            
            parsed_data.append({
                "latitude": geometry["coordinates"][1],
                "longitude": geometry["coordinates"][0],
                "depth": geometry["coordinates"][2],
                "magnitude": properties["mag"],
                "place": properties["place"],
                "time": pd.to_datetime(properties["time"], unit='ms')
            })
            
        return pd.DataFrame(parsed_data)
    
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 사이드바 UI: 연도 선택
current_year = datetime.now().year
selected_year = st.sidebar.slider("연도를 선택하세요", min_value=2000, max_value=current_year, value=current_year)

st.sidebar.info("💡 **Tip:** 데이터 로딩 속도와 렌더링 최적화를 위해 규모(Magnitude) 5.0 이상의 지진만 표시됩니다.")

# 데이터 로딩 스피너
with st.spinner(f'{selected_year}년 지진 데이터를 불러오는 중입니다...'):
    df = fetch_earthquake_data(selected_year)

if not df.empty:
    st.subheader(f"총 {len(df):,}건의 지진 발생 (규모 5.0 이상)")
    
    # PyDeck을 활용한 고급 3D 지도 시각화
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=["longitude", "latitude"],
        get_radius="magnitude * 20000", # 지진 규모에 비례하여 원 크기 설정
        get_fill_color=[255, 50, 50, 150], # 반투명한 붉은색
        pickable=True,
        auto_highlight=True,
    )
    
    view_state = pdk.ViewState(
        latitude=0,
        longitude=0,
        zoom=1,
        pitch=0,
    )
    
    # 툴팁 설정
    tooltip = {
        "html": "<b>장소:</b> {place} <br/><b>규모:</b> {magnitude} <br/><b>일시:</b> {time}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
    
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip, map_style="mapbox://styles/mapbox/dark-v10")
    
    st.pydeck_chart(r)
    
    # 원본 데이터 확인 탭
    with st.expander("원시 데이터(Raw Data) 보기"):
        st.dataframe(df.sort_values(by="time", ascending=False))

else:
    st.warning("선택한 연도에 해당하는 지진 데이터가 없거나, API 응답이 지연되고 있습니다.")
