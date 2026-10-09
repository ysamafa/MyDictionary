"""
MY DICTIONARY - Mobil/Web Tam Sürüm (Hatasız & Eksiksiz)
- Kelime Kartları (✓ / ✗ butonlu, çevirmeli)
- Test Modu ("X kelimesinin anlamı nedir?" soru kalıplı, hiyerarşik şıklı)
- Klasik Mod (Yazarak kontrol)
- Eşleştirme (Kutuları Kutulara Koyma: Havuzdan seç, kutuya bırak, Cevapları Gönder)
- Geniş Kelime & Grup Yönetimi + Sorgula (API) Motoru
"""

import os
import random
import requests
import streamlit as st

st.set_page_config(
    page_title="My Dictionary",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Sabitler
DOSYA_YOLU = os.path.join(os.path.dirname(__file__), "sozluk.txt")
VARSAYILAN_GRUP = "Genel"
SEP = " / "
ESLES_SAYI = 5  # Hata veren eksik tanım buradadır
TURLER = ["Fiil", "Sıfat", "İsim", "Zarf", "Phrasal Verb", "Diğer"]

# ---------------------------------------------------------
# Veri Yardımcıları & API
# ---------------------------------------------------------
def normalize(metin):
    metin = metin.strip().replace("İ", "i").replace("I", "ı").lower()
    return " ".join(metin.split())

def grup_ebeveyn(yol):
    return yol.rsplit(SEP, 1)[0] if SEP in yol else ""

def grup_altinda(grup, ust):
    return grup == ust or grup.startswith(ust + SEP)

def sozluk_oku():
    liste = []
    if not os.path.exists(DOSYA_YOLU):
        return liste
    with open(DOSYA_YOLU, "r", encoding="utf-8-sig") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            p = [x.strip() for x in satir.split(";")]
            if len(p) < 3 or not p[1] or not p[2]:
                continue
            liste.append({
                "tur": p[0],
                "ing": p[1],
                "tr": p[2],
                "grup": p[3] if len(p) > 3 and p[3] else VARSAYILAN_GRUP,
                "oen": p[4] if len(p) > 4 else "",
                "otr": p[5] if len(p) > 5 else ""
            })
    return liste

def sozluk_yaz(kelimeler):
    with open(DOSYA_YOLU, "w", encoding="utf-8") as f:
        f.write("# MY DICTIONARY Kelime Veri Tabanı\n")
        for k in kelimeler:
            s = f"{k['tur']};{k['ing']};{k['tr']};{k['grup']}"
            if k.get("oen") or k.get("otr"):
                s += f";{k.get('oen', '')};{k.get('otr', '')}"
            f.write(s + "\n")

def api_kelime_detay(ing_kelime):
    sonuc = {"es": "", "zit": "", "ornek": ""}
    kelime = ing_kelime.strip().lower()
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r_syn = requests.get(f"https://api.datamuse.com/words?rel_syn={kelime}&max=3", headers=headers, timeout=3)
        if r_syn.status_code == 200:
            sonuc["es"] = ", ".join([x["word"] for x in r_syn.json()])
        r_ant = requests.get(f"https://api.datamuse.com/words?rel_ant={kelime}&max=3", headers=headers, timeout=3)
        if r_ant.status_code == 200:
            sonuc["zit"] = ", ".join([x["word"] for x in r_ant.json()])
    except Exception:
        pass
    try:
        r_dict = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{kelime}", headers=headers, timeout=3)
        if r_dict.status_code == 200:
            veri = r_dict.json()
            if isinstance(veri, list) and veri:
                for meaning in veri[0].get("meanings", []):
                    for defn in meaning.get("definitions", []):
                        if defn.get("example"):
                            sonuc["ornek"] = defn["example"].strip()
                            break
                    if sonuc["ornek"]:
                        break
    except Exception:
        pass
    if not sonuc["ornek"]:
        sonuc["ornek"] = f"He tried to {kelime} during the process."
    return sonuc

# ---------------------------------------------------------
# State Yönetimi
# ---------------------------------------------------------
if "kelimeler" not in st.session_state:
    st.session_state.kelimeler = sozluk_oku()

if "secili_grup" not in st.session_state:
    st.session_state.secili_grup = "Hepsi"

if "secili_tur" not in st.session_state:
    st.session_state.secili_tur = "Hepsi"

def secili_kelimeleri_al():
    grup = st.session_state.secili_grup
    tur = st.session_state.secili_tur
    return [k for k in st.session_state.kelimeler 
            if (tur == "Hepsi" or k["tur"] == tur) and 
               (grup == "Hepsi" or grup_altinda(k["grup"], grup))]

def tum_gruplari_al():
    hepsi = {VARSAYILAN_GRUP} | {k["grup"] for k in st.session_state.kelimeler}
    return sorted(list(hepsi))

# ---------------------------------------------------------
# ÜST MENÜ & FİLTRELER
# ---------------------------------------------------------
st.title("📖 MY DICTIONARY")

with st.expander("⚙️ Filtre & Çalışma Grubu Seçimi", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.secili_tur = st.selectbox("Tür:", ["Hepsi"] + TURLER, index=0)
    with c2:
        gruplar = ["Hepsi"] + tum_gruplari_al()
        st.session_state.secili_grup = st.selectbox("Grup:", gruplar, index=0)
    st.caption(f"Aktif Havuz: {len(secili_kelimeleri_al())} kelime")

# Ana Menü Sekmeleri
sekme_kart, sekme_test, sekme_klasik, sekme_esles, sekme_yonet = st.tabs([
    "🗂️ Kelime Kartı", 
    "📝 Test", 
    "✍️ Klasik", 
    "🧩 Eşleştirme", 
    "📚 Kelimeler & Gruplar"
])

# ---------------------------------------------------------
# 1. KELİME KARTI MODU
# ---------------------------------------------------------
with sekme_kart:
    havuz = secili_kelimeleri_al()
    if not havuz:
        st.warning("Seçili grupta kelime bulunamadı.")
    else:
        if "kk_idx" not in st.session_state:
            st.session_state.kk_idx = 0
            st.session_state.kk_cevrildi = False
            st.session_state.kk_dogru = 0
            st.session_state.kk_yanlis = 0

        k_idx = st.session_state.kk_idx % len(havuz)
        k = havuz[k_idx]

        st.caption(f"Kart {k_idx + 1} / {len(havuz)}  ·  Doğru: {st.session_state.kk_dogru} | Yanlış: {st.session_state.kk_yanlis}")

        with st.container(border=True):
            if not st.session_state.kk_cevrildi:
                st.markdown(f"<span style='background:#FFEDD5; color:#C2410C; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:12px;'>{k['tur'].upper()}</span>", unsafe_allow_html=True)
                st.markdown(f"<h1 style='text-align: center; color: #1E293B; margin: 25px 0;'>{k['ing']}</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 13px;'>Anlamını görmek için Çevir butonuna dokunun ⟳</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h1 style='text-align: center; color: #16A34A; margin: 15px 0;'>{k['tr']}</h1>", unsafe_allow_html=True)
                if k.get("otr"):
                    st.markdown(f"<p style='text-align: center; color: #EA580C; font-size: 15px;'>{k['otr']}</p>", unsafe_allow_html=True)
                if k.get("oen"):
                    st.markdown(f"<p style='text-align: center; color: #64748B; font-style: italic; font-size: 14px;'>\"{k['oen']}\"</p>", unsafe_allow_html=True)

        c_cevir, c_yanlis, c_dogru = st.columns([2, 1, 1])
        with c_cevir:
            if st.button("🔄 Çevir", use_container_width=True, key="kk_btn_cvr"):
                st.session_state.kk_cevrildi = not st.session_state.kk_cevrildi
                st.rerun()
        with c_yanlis:
            if st.button("✗", use_container_width=True, type="secondary", key="kk_btn_y"):
                st.session_state.kk_yanlis += 1
                st.session_state.kk_idx += 1
                st.session_state.kk_cevrildi = False
                st.rerun()
        with c_dogru:
            if st.button("✓", use_container_width=True, type="primary", key="kk_btn_d"):
                st.session_state.kk_dogru += 1
                st.session_state.kk_idx += 1
                st.session_state.kk_cevrildi = False
                st.rerun()

# ---------------------------------------------------------
# 2. TEST MODU (Hiyerarşik Şıklar)
# ---------------------------------------------------------
with sekme_test:
    havuz = secili_kelimeleri_al()
    if len(havuz) < 4:
        st.warning("Test modu için en az 4 kelime gereklidir.")
    else:
        if "test_soru" not in st.session_state:
            hedef = random.choice(havuz)
            ayni_tur = [x["tr"] for x in havuz if x["tur"] == hedef["tur"] and x["tr"] != hedef["tr"]]
            diger = [x["tr"] for x in havuz if x["tr"] != hedef["tr"] and x["tr"] not in ayni_tur]
            random.shuffle(ayni_tur)
            random.shuffle(diger)
            yanlislar = (ayni_tur + diger)[:3]
            tum_siklar = yanlislar + [hedef["tr"]]
            random.shuffle(tum_siklar)
            st.session_state.test_soru = {"hedef": hedef, "siklar": tum_siklar, "cevap": hedef["tr"]}
            st.session_state.test_cevaplandi = False

        s = st.session_state.test_soru
        st.markdown(f"### \"{s['hedef']['ing']}\" kelimesinin anlamı ne demektir?")
        st.caption(f"Tür: {s['hedef']['tur']}  ·  Grup: {s['hedef']['grup']}")

        secilen = st.radio("Seçeneğinizi işaretleyin:", s["siklar"], index=None, key="test_radio")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cevabı Onayla", use_container_width=True, key="test_onay"):
                if secilen:
                    st.session_state.test_cevaplandi = True
                    if secilen == s["cevap"]:
                        st.success("✓ Tebrikler! Doğru cevap.")
                    else:
                        st.error(f"✗ Yanlış! Doğru cevap: {s['cevap']}")
                    if s["hedef"].get("oen"):
                        st.info(f"Örnek: \"{s['hedef']['oen']}\"")
                else:
                    st.warning("Lütfen bir şık seçin.")
        with c2:
            if st.button("Sonraki Soru ➡", use_container_width=True, key="test_next"):
                del st.session_state.test_soru
                st.rerun()

# ---------------------------------------------------------
# 3. KLASİK MOD (Yazarak Kontrol)
# ---------------------------------------------------------
with sekme_klasik:
    havuz = secili_kelimeleri_al()
    if not havuz:
        st.warning("Seçili grupta kelime bulunamadı.")
    else:
        if "kl_hedef" not in st.session_state:
            st.session_state.kl_hedef = random.choice(havuz)
            st.session_state.kl_cevaplandi = False

        k = st.session_state.kl_hedef
        st.markdown(f"<h2 style='text-align: center; color: #0F766E;'>{k['ing']}</h2>", unsafe_allow_html=True)
        st.caption(f"Tür: {k['tur']} · Grup: {k['grup']}")

        girilen = st.text_input("Türkçe karşılığını yazın:", key="kl_input").strip()

        col_k1, col_k2 = st.columns(2)
        with col_k1:
            if st.button("Kontrol Et", use_container_width=True, key="kl_btn_chk"):
                if girilen:
                    st.session_state.kl_cevaplandi = True
                    if normalize(girilen) == normalize(k["tr"]):
                        st.success(f"✓ Doğru! ({k['tr']})")
                    else:
                        st.error(f"✗ Yanlış. Doğru cevap: {k['tr']}")
                    if k.get("oen"):
                        st.info(f"Örnek Cümle: \"{k['oen']}\"")
                else:
                    st.warning("Lütfen bir cevap yazın.")
        with col_k2:
            if st.button("Yeni Kelime ➡", use_container_width=True, key="kl_btn_nxt"):
                del st.session_state.kl_hedef
                st.rerun()

# ---------------------------------------------------------
# 4. EŞLEŞTİRME MODU (Kutuları Kutulara Koyma)
# ---------------------------------------------------------
with sekme_esles:
    havuz = secili_kelimeleri_al()
    if len(havuz) < ESLES_SAYI:
        st.warning(f"Eşleştirme için en az {ESLES_SAYI} kelime gereklidir.")
    else:
        if "esles_tur" not in st.session_state:
            secilenler = random.sample(havuz, ESLES_SAYI)
            st.session_state.esles_tur = {
                "kelimeler": secilenler,
                "ing_list": random.sample([x["ing"] for x in secilenler], ESLES_SAYI),
                "tr_list": [x["tr"] for x in secilenler],
                "sonuclar": None
            }

        e = st.session_state.esles_tur
        st.markdown("##### Soldaki Türkçe kelimeler için uygun İngilizce kutuyu seçin:")

        kullanici_eslesmeleri = {}
        with st.container(border=True):
            for i, tr_kelime in enumerate(e["tr_list"]):
                col_tr, col_ing = st.columns([1, 1])
                with col_tr:
                    st.markdown(f"**{tr_kelime}**")
                with col_ing:
                    secim = st.selectbox(
                        f"{tr_kelime} karşılığı:",
                        ["Boş"] + e["ing_list"],
                        key=f"esles_sec_{i}",
                        label_visibility="collapsed"
                    )
                    kullanici_eslesmeleri[tr_kelime] = secim

        col_es1, col_es2 = st.columns(2)
        with col_es1:
            if st.button("Cevapları Gönder", use_container_width=True, type="primary", key="esles_btn_gonder"):
                if "Boş" in kullanici_eslesmeleri.values():
                    st.warning("Lütfen tüm eşleştirmeleri doldurun.")
                else:
                    dogru_say = 0
                    for k in e["kelimeler"]:
                        if kullanici_eslesmeleri.get(k["tr"]) == k["ing"]:
                            dogru_say += 1
                    e["sonuclar"] = (dogru_say, ESLES_SAYI - dogru_say)
                    st.rerun()

        with col_es2:
            if st.button("Yeni Tahta ➡", use_container_width=True, key="esles_btn_yeni"):
                del st.session_state.esles_tur
                st.rerun()

        if e.get("sonuclar"):
            d, y = e["sonuclar"]
            with st.container(border=True):
                st.markdown(f"### Sonuç: {d} Doğru / {y} Yanlış")
                for k in e["kelimeler"]:
                    sec = kullanici_eslesmeleri.get(k["tr"])
                    if sec == k["ing"]:
                        st.markdown(f"✓ **{k['tr']}** = {k['ing']}")
                    else:
                        st.markdown(f"✗ **{k['tr']}** = Doğrusu: *{k['ing']}* (Seçilen: {sec})")

# ---------------------------------------------------------
# 5. KELİME & GRUP YÖNETİMİ
# ---------------------------------------------------------
with sekme_yonet:
    y_ekle, y_liste = st.tabs(["➕ Kelime Ekle", "📋 Tüm Kelimeler"])
    
    with y_ekle:
        ing_val = st.text_input("İngilizce:", key="yonet_ing")
        
        if st.button("Sorgula (API)", key="yonet_sorgula"):
            if ing_val:
                with st.spinner("Bilgiler Sorgulanıyor..."):
                    res = api_kelime_detay(ing_val)
                    st.session_state.form_es = res["es"]
                    st.session_state.form_zit = res["zit"]
                    st.session_state.form_ornek = res["ornek"]
                    st.success("✓ Bilgiler getirildi!")
            else:
                st.warning("Lütfen önce kelime yazın.")

        tr_val = st.text_input("Türkçe Karşılığı:", key="yonet_tr")
        tur_val = st.selectbox("Tür:", TURLER, key="yonet_tur")
        grup_val = st.text_input("Grup:", value=VARSAYILAN_GRUP, key="yonet_grup")

        es_val = st.text_input("Eş Anlam:", value=st.session_state.get("form_es", ""), key="yonet_es")
        zit_val = st.text_input("Zıt Anlam:", value=st.session_state.get("form_zit", ""), key="yonet_zit")
        ornek_val = st.text_input("Örnek Cümle:", value=st.session_state.get("form_ornek", ""), key="yonet_ornek")

        if st.button("Kelimeyi Kaydet", type="primary", use_container_width=True, key="yonet_kaydet"):
            if ing_val and tr_val:
                detay = f"Eş: {es_val} | Zıt: {zit_val}" if (es_val or zit_val) else ""
                yeni = {
                    "tur": tur_val, "ing": ing_val.strip(), "tr": tr_val.strip(),
                    "grup": grup_val.strip() or VARSAYILAN_GRUP,
                    "oen": ornek_val.strip(), "otr": detay
                }
                st.session_state.kelimeler.append(yeni)
                sozluk_yaz(st.session_state.kelimeler)
                st.success(f"✓ '{ing_val}' başarıyla kaydedildi!")
            else:
                st.error("İngilizce ve Türkçe alanları zorunludur.")

    with y_liste:
        ara = st.text_input("🔍 Filtrele:", key="yonet_ara")
        tablo_verisi = []
        for k in st.session_state.kelimeler:
            if not ara or ara.lower() in k["ing"].lower() or ara.lower() in k["tr"].lower():
                es_z = k.get("otr", "")
                tablo_verisi.append({
                    "Tür": k["tur"],
                    "Grup": k["grup"],
                    "İngilizce": k["ing"],
                    "Türkçe": k["tr"],
                    "Detay (Eş/Zıt)": es_z,
                    "Örnek Cümle": k.get("oen", "")
                })
        st.dataframe(tablo_verisi, use_container_width=True, hide_index=True)
