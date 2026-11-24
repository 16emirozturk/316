"""Çoklu yönetici hesabı yükleme ve doğrulama testleri."""
from __future__ import annotations

import ast
from pathlib import Path

import guvenlik

ROOT = Path(__file__).resolve().parents[1]


def _iki_hesapli_secrets():
    return {
        "admins": {
            "mudur": {
                "username": "okul_muduru",
                "password_hash": guvenlik.parola_hashle("Mudur-Test-Parola-2026!", iterasyon=100_000),
            },
            "rehberlik": {
                "username": "rehberlik",
                "password_hash": guvenlik.parola_hashle("Rehberlik-Test-Parola-2026!", iterasyon=100_000),
            },
        }
    }


def test_iki_yonetici_hesabi_yuklenir_ve_ayri_ayri_giris_yapar():
    ayarlar = _iki_hesapli_secrets()
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(ayarlar)

    assert hata == ""
    assert len(hesaplar) == 2
    assert guvenlik.kimlik_dogrula_hesaplar(
        "okul_muduru", "Mudur-Test-Parola-2026!", hesaplar
    ) == "okul_muduru"
    assert guvenlik.kimlik_dogrula_hesaplar(
        "rehberlik", "Rehberlik-Test-Parola-2026!", hesaplar
    ) == "rehberlik"


def test_kullanici_adi_buyuk_kucuk_harf_ve_bosluk_duyarsizdir():
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(_iki_hesapli_secrets())
    assert hata == ""
    assert guvenlik.kimlik_dogrula_hesaplar(
        "  OKUL_MUDURU  ", "Mudur-Test-Parola-2026!", hesaplar
    ) == "okul_muduru"


def test_hatali_kullanici_ve_parola_genel_basarisiz_sonuc_verir():
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(_iki_hesapli_secrets())
    assert hata == ""
    assert guvenlik.kimlik_dogrula_hesaplar("olmayan", "yanlis", hesaplar) is None
    assert guvenlik.kimlik_dogrula_hesaplar(
        "okul_muduru", "yanlis-parola", hesaplar
    ) is None


def test_yinelenen_kullanici_adlari_reddedilir():
    ozet = guvenlik.parola_hashle("Test-Parolasi-123!", iterasyon=100_000)
    ayarlar = {
        "admins": {
            "bir": {"username": "Rehberlik", "password_hash": ozet},
            "iki": {"username": "rehberlik", "password_hash": ozet},
        }
    }
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(ayarlar)
    assert hesaplar == []
    assert "benzersiz" in hata


def test_coklu_hesaplarda_duz_metin_parola_reddedilir():
    ayarlar = {
        "admins": {
            "mudur": {"username": "mudur", "password_hash": "parola123"}
        }
    }
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(ayarlar)
    assert hesaplar == []
    assert "PBKDF2" in hata


def test_legacy_tek_admin_ayari_geriye_donuk_desteklenir():
    ozet = guvenlik.parola_hashle("Eski-Hesap-Test-2026!", iterasyon=100_000)
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(
        {"admin": {"username": "admin_eski", "password_hash": ozet}}
    )
    assert hata == ""
    assert guvenlik.kimlik_dogrula_hesaplar(
        "admin_eski", "Eski-Hesap-Test-2026!", hesaplar
    ) == "admin_eski"


def test_en_fazla_on_hesap_kabul_edilir_on_birinci_reddedilir():
    hashler = guvenlik.parola_hashle("Test-Parolasi-123!", iterasyon=100_000)
    on_hesap = {
        "admins": {
            f"hesap_{i}": {"username": f"yonetici_{i}", "password_hash": hashler}
            for i in range(10)
        }
    }
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(on_hesap)
    assert len(hesaplar) == 10
    assert hata == ""

    on_bir_hesap = {"admins": {**on_hesap["admins"], "hesap_10": {
        "username": "yonetici_10", "password_hash": hashler
    }}}
    hesaplar, hata = guvenlik.yonetici_hesaplarini_yukle(on_bir_hesap)
    assert hesaplar == []
    assert "10" in hata


def test_giris_akisi_mevcut_kilit_ve_oturum_surelerini_korur():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)
    constants = {
        node.targets[0].id: ast.unparse(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {
            "OTURUM_ZAMAN_ASIMI_SN", "OTURUM_HATALI_ESIK", "OTURUM_KILIT_SN", "GLOBAL_HATALI_ESIK"
        }
    }
    assert constants == {
        "OTURUM_ZAMAN_ASIMI_SN": "30 * 60",
        "OTURUM_HATALI_ESIK": "5",
        "OTURUM_KILIT_SN": "5 * 60",
        "GLOBAL_HATALI_ESIK": "20",
    }
    assert "kimlik_dogrula_rol" in app_source
    assert "yonetici_rol=rol" in app_source
    assert "sayfa_kurucu_girisi" in app_source
