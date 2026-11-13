# Book sales dashboard — simplified version

## Red book theme

Kitap temasinda acik krem zemin, koyu murdum/komur yan alan ve kirmizi vurgular kullanilir.
Gecmis degerler gri, ileri tahmin kirmizi, daha kalin ve kesikli cizgiyle ayirt edilir.
Basliklar serif, govde metinleri sans-serif yazi tipindedir. Urun siniflarinin renkli aciklama etiketleri vardir.
Kirmizi tema ve sade filtreler korunur. Tahmin yontemi asagida aciklanan ufka uygun testlerle otomatik secilir.
Tema ayarlari .streamlit/config.toml dosyasindadir; ek CSS/HTML/JavaScript yazilmamistir.

Python ile yazilmis ISL467E odev uygulamasi. Arayuz Ingilizcedir.
Para birimi kullanici tarafindan Turk lirasi olarak dogrulanmistir; finansal degerler ₺ ile gosterilir.
Ek HTML, CSS veya JavaScript kodu bulunmaz.

## Nasil kullanilir?

1. Soldaki Period ile tarih araligini secin. Isterseniz Category ve City ile daraltin.
2. Ustte Overview, Customers, Products veya Forecast bolumunu secin.
3. Kartlardaki yardim simgelerine gelerek tanimlari okuyun; grafiklerde nokta/cubuk uzerine gelerek degerleri gorun.
4. Filtreler otomatik uygulanir ve bolumler arasinda korunur. All categories / All cities secenekleri filtreyi kaldirir.

Overview satis, siparis, adet ve sehir dagilimini gosterir.
Customers tekrar satin alan musterileri ve musteri degerini aciklar.
Products satis onemine gore ABC ve tam aylardaki adet degiskenligine gore XYZ siniflarini ozetler.
Forecast yalnizca adet/satis ve 4/8/12 haftalik ufuk secimini sunar.
Data notes veri temizligini ve secili kayitlari aciklar.

## Otomatik tahmin nasil secilir?

Kullanici sadece hedefi ve 4/8/12 haftalik ufku secer; ek bir model secme dugmesi yoktur.
Her ufuk icin son h hafta bagimsiz test olarak ayrilir ve model seciminde kullanilmaz.
Onceki verilerde son 2 veya 3 cakismayan h haftalik pencere sirayla tahmin edilir.
Her baslangicta yalnizca onceki haftalar egitime katilir; boylece ilerideki sonuc egitime sizmaz.

Dort basit aday vardir: Son hafta, son 4 hafta ortalamasi, agirlikli 4 hafta ortalamasi ve dogrusal trend.
Agirliklar eskiden yeniye 1, 2, 3, 4'tur. Adaylar ayni gercekler ve ayni h haftalik pencerelerle karsilastirilir.
Toplam dogrulama mutlak hatasi en dusuk yontem otomatik secilir. Esitlikte listedeki daha basit yontem tercih edilir.
MAE ve WAPE, ayni gercekler uzerinde hesaplandigindan ayni model siralamasini verir.

Secimden sonra secilen yontem son h haftalik bagimsiz testte bir kez kontrol edilir.
Kartta **Independent test error** olarak bu donemin WAPE'si gosterilir. Karsilastirma tablosu ise model-secim
pencerelerinin **Validation** hatalarini gosterir; bunlar farkli amaclarla ayrilmis donemlerdir.
Son olarak ayni secili yontem tum gozlenen haftalarla yeniden kurularak ileri h haftayi tahmin eder.
Model secimi bagimsiz test sonucuna gore tekrar degistirilmez; gelecek basarisi garanti edilmez.

En az 12 ilk egitim haftasi, 2 dogrulama penceresi ve 1 bagimsiz test penceresi gerekir.
Dolayisiyla 4 hafta icin en az 24, 8 hafta icin 36, 12 hafta icin 48 tam hafta gerekir.
Yetersiz donemde model zorla kurulmaz; daha genis tarih araligi veya kisa ufuk istenir.
Tum test gercekleri oldugu gibi tutulur; aykiri sonuc ve sifir satis haftalari testten silinmez.
MAE/RMSE hedef birimindedir; WAPE toplam mutlak hatanin toplam gercege yuzdesidir.
Sifir gercek varsa MAPE, toplam gercek sifirsa WAPE, hedef sabitse R2 tanimsizdir.
Ekrandaki hata orani gelecek icin garanti veya guven araligi degildir.

Secilen son-hafta veya ortalama yontemleri ileri haftalarda sabit deger uretir; bu hesap hatasi degildir.
Sabit cikti varsa yontem ve nedeni gorunur bir aciklamada belirtilir. Yapay dalgalanma eklenmez.
Eski %59'luk hata, tek seferlik 16 haftalik trend testine aitti; yeni h haftalik bagimsiz testle dogrudan karsilastirilmaz.

Tahminler son tam gozlem haftasinin ardindan baslar. Eksik son hafta varsa ilk tahmin o haftayi kapsayabilir.
Kaynak 2020'ye ait oldugundan bunlar bugunun tarihinden baslayan tahminler degildir.
Satissiz haftalar sifir kabul edilir; stoksuzluk ile talep eksikligi ayirt edilemez.
Yillik mevsimsellik, stok/siparis miktari ve emniyet stogu bu sinirli veriden varsayilmaz.
Senaryo girdileri, model secici, aykiri deger ayarlari, alt sekmeler ve coklu indirme dugmeleri ana arayuzden kaldirilmistir.

## Veri ve urun siniflari

SalesAmount = Quantity × NetPrice. Bu satis degeridir; kar degildir. UnitPrice maliyet olarak kullanilmaz.
664.154 kaynak satirindan 657.925 pozitif satis satiri tutulmustur.
6.213 tam tekrar, 6 gecersiz temel alan ve 10 sifir/pozitif olmayan islem ayrilmistir.
Eksik sehir/kategori Unknown olarak tutulur. Negatif miktarlar olasi iade olarak ayrilir.
Tam tekrarlarin mukerrer kayit oldugu bir analiz varsayimidir; kaynak satir kimligi bulunmaz.
Sayimlar data_quality.json ve Data notes ekraninda yer alir.

ABC: satis degerine gore urunleri sirala; A yaklasik ilk %80, B sonraki %15, C kalan.
Esigi asan urun mevcut grupta kalir; ilk urun A olur. Gercek pay ayrica hesaplanir.
XYZ: en az 3 tam takvim ayindaki adetlerin ornek standart sapmasi / ortalamasi.
X <= 0,5; Y <= 1; Z > 1; yetersiz gecmis veya sifir ortalamada N/A.
Aradaki satissiz aylar sifirdir; yeni urun ve stok bulunabilirligi bilgisi olmamasi sinirliliktir.

## Calistirma (Python 3.12)

Bu klasorde terminal acin:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Veri degisirse: `.\.venv\Scripts\python.exe prepare_dataset.py`.
Uygulama hazir Parquet'in kaynak Excel ile SHA-256 eslesmesini kontrol eder; eslesmezse Excel'i temizleyerek okur.
Eski B2B_Transaction_Data_prepared.parquet kullanilmaz.

## Kod sirasi ve kontroller

- streamlit_app.py: bes temel bolum ve ortak filtreler.
- dashboard_utils.py: TL bicimi, aciklamali kartlar ve ortak grafikler.
- data_analysis.py: temizlik, ABC/XYZ ve toplamlar.
- forecast.py: tahmin hesaplari ve sade tahmin ekrani.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Arayuz kontrolleri tum bolumleri, ortak filtreleri, tek kategori secimini, TL ve yardim metinlerini,
uc farkli tahmin ufkunu, otomatik yontem aciklamasini ve kisa donem uyarilarini kapsar.
Hesap kontrolleri bagimsiz testin model secimini ve test tahminlerini degistirmemesini,
ufka uygun cakismayan pencereleri, yetersiz gecmisi, sifir hedefte hata olcumunu ve tam veriyle yeniden kurmayi kapsar.
Veri temizligi, eksik ay/hafta, ABC esik urunu ve XYZ adet-fiyat ayrimi kontrolleri de korunmustur.

Streamlit Cloud: ana dosya streamlit_app.py, Python 3.12. Excel, yeni temiz Parquet, JSON,
Python dosyalari, requirements ve .streamlit/config.toml birlikte yuklenmelidir. .venv yuklenmez.
Bu paket yerel calisma surumudur; canli uygulama ayrica guncellenip kontrol edilmelidir.
