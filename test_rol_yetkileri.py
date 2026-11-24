from __future__ import annotations

import guvenlik


def _secrets():
    return {
        "hesaplar": {
            "yonetici": {"username": "okul_yonetici", "password_hash": guvenlik.parola_hashle("Manager-Test-2026!", iterasyon=100_000)},
            "kurucu": {"username": "kurucu", "password_hash": guvenlik.parola_hashle("Founder-Test-2026!", iterasyon=100_000)},
        }
    }


def test_iki_rol_hesabi_yuklenir():
    hesaplar, hata = guvenlik.rol_hesaplarini_yukle(_secrets())
    assert hata == ""
    assert set(hesaplar) == {"yonetici", "kurucu"}


def test_yonetici_ve_kurucu_girisleri_birbirinden_ayridir():
    hesaplar, hata = guvenlik.rol_hesaplarini_yukle(_secrets())
    assert hata == ""
    assert guvenlik.kimlik_dogrula_rol("okul_yonetici", "Manager-Test-2026!", hesaplar["yonetici"])
    assert not guvenlik.kimlik_dogrula_rol("kurucu", "Founder-Test-2026!", hesaplar["yonetici"])
    assert guvenlik.kimlik_dogrula_rol("kurucu", "Founder-Test-2026!", hesaplar["kurucu"])
    assert not guvenlik.kimlik_dogrula_rol("okul_yonetici", "Manager-Test-2026!", hesaplar["kurucu"])


def test_kullanici_adlari_benzersiz_olmali():
    hash_a = guvenlik.parola_hashle("Password-2026!A", iterasyon=100_000)
    hash_b = guvenlik.parola_hashle("Password-2026!B", iterasyon=100_000)
    ayarlar = {"hesaplar": {
        "yonetici": {"username": "ORTAK", "password_hash": hash_a},
        "kurucu": {"username": "ortak", "password_hash": hash_b},
    }}
    hesaplar, hata = guvenlik.rol_hesaplarini_yukle(ayarlar)
    assert hesaplar == {}
    assert "farklı" in hata


def test_eksik_rol_yapilandirmasi_reddedilir():
    hash_a = guvenlik.parola_hashle("Password-2026!A", iterasyon=100_000)
    hesaplar, hata = guvenlik.rol_hesaplarini_yukle({"hesaplar": {
        "yonetici": {"username": "okul_yonetici", "password_hash": hash_a}
    }})
    assert hesaplar == {}
    assert "kurucu" in hata


def test_rol_sayfa_yetkileri_veri_minimizasyonunu_korur():
    assert guvenlik.sayfaya_erisim_var_mi("yonetici", "Bildirim inceleme")
    assert not guvenlik.sayfaya_erisim_var_mi("kurucu", "Bildirim inceleme")
    assert guvenlik.sayfaya_erisim_var_mi("kurucu", "Yedekleme ve geri yükleme")
    assert not guvenlik.sayfaya_erisim_var_mi("yonetici", "Yedekleme ve geri yükleme")
    assert not guvenlik.sayfaya_erisim_var_mi("kurucu", "Etki Merkezi")
    assert guvenlik.sayfaya_erisim_var_mi("kurucu", "PDF proje raporu")


def test_yonetim_sayfalari_kendi_rol_kontrolunu_yapar():
    from pathlib import Path
    import ast

    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)
    expected = {
        "sayfa_inceleme": "Bildirim inceleme",
        "sayfa_istatistikler": "İstatistikler",
        "sayfa_trend": "Trend ve ortam",
        "sayfa_etki_merkezi": "Etki Merkezi",
        "sayfa_takvim": "Önleyici çalışma takvimi",
        "sayfa_bildirim_merkezi": "Yönetici bildirim merkezi",
        "sayfa_yonetim_gunlugu": "Yönetim günlüğü",
        "sayfa_pdf_rapor": "PDF proje raporu",
        "sayfa_yedekleme": "Yedekleme ve geri yükleme",
    }
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for function_name, page_name in expected.items():
        calls = [node for node in ast.walk(functions[function_name])
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "yonetici_gerekli"]
        assert calls, f"{function_name} has no authorization guard"
        assert any(call.args and isinstance(call.args[0], ast.Constant)
                   and call.args[0].value == page_name for call in calls)


def test_oturum_kilit_sureleri_degisiklige_ugramadi():
    from pathlib import Path
    import ast

    tree = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {"OTURUM_ZAMAN_ASIMI_SN", "OTURUM_HATALI_ESIK", "OTURUM_KILIT_SN", "GLOBAL_HATALI_ESIK"}:
                values[node.targets[0].id] = ast.unparse(node.value)
    assert values == {"OTURUM_ZAMAN_ASIMI_SN": "30 * 60", "OTURUM_HATALI_ESIK": "5",
                      "OTURUM_KILIT_SN": "5 * 60", "GLOBAL_HATALI_ESIK": "20"}
