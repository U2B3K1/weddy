"""Telegram vidjetlari (Bot API 10.4): xabar ichida ishlaydigan kichik interfeys — rahbarning «Bugun», «To'lov» va
xodimning «Sozlamalar» ekranlari.

Vidjet — bitta HTML (kodi yuborilgach o'zgarmaydi) + bot o'zgartiradigan holat (`chat_data`, 1024 baytgacha JSON).
Cheklovlar (core.telegram.org/bots/widgets): tarmoq yo'q; faqat umumiy shrift turlari (serif, system-ui — nomli
shriftlar olib tashlanadi); matn kiritish yo'q (faqat `button`); HTML 32 KB, zlib bilan siqilganda 4096 baytgacha;
balandlik 600 px gacha, ichida aylantirish yo'q; `filter` da faqat blur/brightness, `text-shadow` yo'q;
`backdrop-filter` bir vaqtda 2 ta elementdan oshsa vidjet to'xtaydi — shuning uchun ishlatilmaydi (fon o'zi xira).
Vidjetni tanimaydigan ilovada xabar izohi (caption) ko'rinadi — shuning uchun izohga doim to'liq matn yoziladi.

Ko'rinish ilovadan (frontend/src/yangi-dizayn.css): saroy zali fonida shisha kartalar, tilla urg'u, serif sarlavha.
Sozlama: `PlatformaSozlama.bot_vidjet` (standart o'chiq) — ega botda `/vidjet` bilan namunani ko'rib, keyin yoqadi.
"""
import json
import re

from django.utils import timezone

from apps.tenants.models import Xodim

from . import telegram

MALUMOT_MAKS = 1024  # chat_data chegarasi (bayt)

# Fon — ilovadagi saroy zali surati (frontend/public/kelinlar/saroy.jpg), juda kichik nusxa: vidjet tarmoqdan rasm
# yuklay olmaydi, HTML esa siqilganda 4 KB dan oshmasligi kerak. Xira ko'rinishi ataylab — ustida shisha kartalar turadi.
FON = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABIMDRANCxIQDhAUExIVGywdGxgYGzYnKSAsQDlEQz85Pj1HUGZXR0thTT0+WXlaYWltcnNyRVV9hnxvhWZwcm7/2wBDARMUFBsXGzQdHTRuST5Jbm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm7/wAARCAAzACwDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAQCAwUBBv/EAC4QAAICAQQABQEHBQAAAAAAAAECAxEABBIhMQUTQVFhIhQjQmJxgZFzorHB0f/EABgBAQEBAQEAAAAAAAAAAAAAAAABAgQD/8QAGBEBAQEBAQAAAAAAAAAAAAAAABEBIRL/2gAMAwEAAhEDEQA/ABCQBvsEHm81/B5o4lIG3ex5vsj4zO10W0CReaHB9/1xODUEyAfOc+c2uje49uJQRZB/jKdTqAiG6A926zNj1DCI8sMQ8SnIjs++a9seFUzJ5r7KCk2Bi7eczHy1YgewyuBjO203R7rvNTykUAOxU10GoDMR6Efte5QhPAiFA/J7/jKtMiiYUtk/4wZAZ2/pQj+4YxpDBERYJdgBQ4rLvExqhCiGlJ47GLeJRRrpNzgW3QGTj1RCEBiOMpmliZSZwW6Fj0wYz9NsiYkEAMDR/bOy6tXEbuTbIDZHedSOPzF2DizzXY2tkBEraXTW1fdD0+TiFXLp2dt4s7kQcflwHhskrqQSM1IwB2fQcVj8E2nUAEUfWxebjFZcGgdyEJIvi/nF9T4bIw5JBXjPQyGCdkIk2lTwF6zr6jT1TEP+2IV5qLSNGQDfH/CP95DyCsUUe4fQgXnNqV42Y7bFnFqFDs8elYhS6yNTc/hGTV245wwyomHYVRIwZjR5wwyKgrtuIvKWdqX6j1hhjR//2Q=='

# Uchala vidjetga umumiy: fon, «LIBOSA» yozuvi, sana/salon belgisi, sarlavha, shisha karta, tugmalar
_CSS = """html{background:#0D1320}
body{margin:0;position:relative;overflow:hidden;color:#F5F2EE;font:14px/1.35 system-ui,sans-serif;padding:14px 14px 12px}
#fon{position:absolute;z-index:-1;left:-14px;top:-14px;right:-14px;bottom:-14px;filter:blur(4px);background:radial-gradient(90% 45% at 50% 0,rgba(243,191,112,.24),transparent 70%),linear-gradient(rgba(13,19,32,.4),rgba(13,19,32,.84)),url(data:image/jpeg;base64,@FON@) center 30%/cover}
.b{display:flex;justify-content:space-between;align-items:center;gap:10px}
.w{font:600 19px/1 ui-serif,serif;letter-spacing:.2em;color:#F6E7CC}
.c{font-size:12px;font-weight:600;padding:6px 10px;border-radius:10px;background:rgba(14,19,30,.55);border:1px solid rgba(255,255,255,.12);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60%}
h1,h2{margin:0;font-family:ui-serif,serif;font-weight:600}
h1{margin-top:12px;font-size:30px;line-height:1.05}
h2{font-size:18px;margin-bottom:4px}
.p{font-size:12.5px;color:#C9CCD4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.g{margin-top:10px;padding:12px;border-radius:16px;border:1px solid rgba(236,190,120,.42);background:linear-gradient(150deg,rgba(255,255,255,.15),rgba(255,255,255,.05) 34%,rgba(255,255,255,.015) 68%),rgba(14,19,30,.5);box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 14px 34px rgba(0,0,0,.34)}
svg{width:22px;height:22px;display:block;flex:none}
.s{font-size:12.5px;color:#C9CCD4}
.n{margin-top:8px}
.d{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
button{display:inline-flex;align-items:center;justify-content:center;gap:6px;font:700 13px/1.2 system-ui,sans-serif;color:#F3BF70;background:rgba(243,191,112,.08);border:1px solid #F3BF70;border-radius:999px;padding:8px 14px}
button svg{width:15px;height:15px}
button:disabled{opacity:.55}
"""
# Umumiy JS: son (3 xonadan bo'sh joy), HTML ekranlash, chiziqli belgi, sarlavha qismi
_JS = """var W=window.TelegramWidget,a=document.getElementById('a');
function f(n){return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')}
function e(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ic(p){return'<svg viewBox="0 0 24 24" fill=none stroke=currentColor stroke-width=2 stroke-linecap=round stroke-linejoin=round>'+p+'</svg>'}
function bs(c,t,p){return'<div class=b><span class=w>LIBOSA</span>'+(c?'<span class=c>'+c+'</span>':'')+'</div><h1>'+t+'</h1>'+(p?'<div class=p>'+p+'</div>':'')}
function yo(d){if(!d){a.innerHTML='<div class=s>Ma\\'lumot yo\\'q. Menyudan qayta oching.</div>';return 1}}
"""


def _vidjet(css, js):
    return ('<style>' + _CSS + css + '</style><div id=fon></div><div id=a></div><script>' + _JS + js
            + '</script>').replace('@FON@', FON)


def _json(d):
    return json.dumps(d, ensure_ascii=False, separators=(',', ':'))


# ---------- «Bugun» (rahbar) ----------

BUGUN_HTML = _vidjet("""
.m{display:flex;gap:12px;align-items:center}
.i{flex:none;width:42px;height:42px;border-radius:12px;display:grid;place-items:center;background:rgba(243,191,112,.14);border:1px solid rgba(243,191,112,.45);color:#F3BF70}
.t{font-size:26px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums}
.t small{font-size:15px;font-weight:700}
.z{height:6px;border-radius:3px;margin:12px 0 6px;overflow:hidden;display:flex;gap:2px}
.z i{display:block;height:100%}
.q,.r{display:flex;align-items:center;font-size:13px;color:#D4D7DE;padding:2px 0}
.q b,.r b{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:700;color:#F5F2EE}
.r{gap:10px;padding:4px 0}
.r b{font-size:15px}
.o{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;color:#0D1320}
.o svg{width:13px;height:13px;stroke-width:3}
.f{margin-top:12px;display:flex;justify-content:space-between;align-items:center;gap:8px}
""", """var R=['#F3BF70','#79A9F2','#62D4A3','#C79BE8','#F08089'],
O=['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentabr','oktabr','noyabr','dekabr'];
function sn(s){var p=String(s||'').split('.');return p.length==3&&O[p[1]-1]?(+p[0])+' '+O[p[1]-1]+', '+p[2]:e(s)}
function ch(s){var d;try{d=JSON.parse(s)}catch(x){}
if(yo(d))return;
var j=d.t||0,u=[['Naqd',d.n]].concat(d.u||[]).filter(function(p){return p[1]>0}),h=bs(d.d&&sn(d.d),'Bugun',e(d.s)+(d.v?' · '+e(d.v)+' holatiga':''));
h+='<div class=g><div class=m><span class=i>'+ic('<ellipse cx=12 cy=5 rx=9 ry=3 /><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>')+'</span><div><div class=s>Bugungi tushum</div><div class=t>'+f(j)+' <small>so\\'m</small></div></div></div>';
h+=u.length&&j>0?'<div class=z>'+u.map(function(p,i){return'<i style="width:'+(p[1]/j*100)+'%;background:'+R[i%5]+'"></i>'}).join('')+'</div>'+u.map(function(p,i){return'<div class=q><i class=d style="background:'+R[i%5]+'"></i>'+e(p[0])+'<b>'+f(p[1])+'</b></div>'}).join(''):'<div class="s n">Bugun hali tushum yo\\'q</div>';
h+='</div><div class=g><h2>Zakaz va libos</h2>'+[['Yangi bron',d.y,'#62D4A3','M12 5v14M5 12h14'],['Berildi',d.b,'#79A9F2','M7 17 17 7M8 7h9v9'],['Qaytdi',d.q,'#F3BF70','M17 7 7 17M16 17H7V8']].map(function(p){return'<div class=r><span class=o style="background:'+p[2]+'">'+ic('<path d="'+p[3]+'"/>')+'</span>'+p[0]+'<b>'+e(p[1])+'</b></div>'}).join('')+'</div>';
var k=d.o?'<i class=d style="background:#62D4A3"></i>Smena ochiq':d.f==null?'Bugun smena yopilmagan':d.f==0?'<i class=d style="background:#62D4A3"></i>Kassa farqsiz':'<i class=d style="background:#F08089"></i>Kassa farqi: '+f(d.f)+' so\\'m';
h+='<div class=f><span class=s>'+k+'</span><button id=y>'+ic('<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>')+'Yangilash</button></div>';
a.innerHTML=h;var y=document.getElementById('y');
if(!W||!W.viewer||!d.x){y.style.display='none';return}
y.onclick=function(){y.disabled=true;y.textContent='…';W.request('b:'+d.x).then(function(r){ch(r&&r.result||W.chatData)},function(){y.disabled=false;y.textContent='Qayta urinish'})}}
ch(W&&W.chatData);if(W){W.onEvent('chatDataChanged',function(){ch(W.chatData)});W.ready&&W.ready()}
""")


def bugun_malumot(salon, xodim_id=0, bugun=None):
    """«Bugun» vidjeti holati — ixcham JSON (kalitlar bir harfli: 1024 baytga sig'ishi kerak)."""
    from .management.commands.kunlik_hisobot import kunlik_raqamlar
    bugun = bugun or timezone.localdate()
    r = kunlik_raqamlar(salon, bugun)
    d = {'x': xodim_id, 's': salon.nomi[:40], 'd': f'{bugun:%d.%m.%Y}', 'v': f'{timezone.localtime():%H:%M}',
         't': r['tushum'], 'n': r['naqd'], 'u': [[nom[:16], s] for nom, s in r['naqdsiz']][:4],
         'y': r['yangi'], 'b': r['berilgan'], 'q': r['qaytgan'], 'f': r['farq'], 'o': r['ochiq']}
    matn = _json(d)
    if len(matn.encode()) > MALUMOT_MAKS:  # juda uzun nomlar — to'lov usullari bo'limisiz
        d['u'] = []
        matn = _json(d)
    return matn


def bugun_vidjeti(x):
    """Dispetcher uchun: `_javob_yubor` shu lug'atni ko'rsa `sendWidget` qiladi, bo'lmasa matnning o'zi ketadi."""
    return {'vidjet': {'html': BUGUN_HTML, 'chat_data': bugun_malumot(x.salon, x.id), 'allow_queries': True}}


NAMUNA = {'x': 0, 's': 'Namuna salon', 'd': '', 'v': '', 't': 4_850_000, 'n': 2_600_000,
          'u': [['Karta', 1_500_000], ["O'tkazma", 750_000]], 'y': 3, 'b': 2, 'q': 1, 'f': None, 'o': True}


def namuna_vidjeti():
    """Ega uchun: o'ylab topilgan raqamlar bilan ko'rinish namunasi (haqiqiy salon ma'lumoti emas)."""
    d = {**NAMUNA, 'd': f'{timezone.localdate():%d.%m.%Y}', 'v': f'{timezone.localtime():%H:%M}'}
    return {'vidjet': {'html': BUGUN_HTML, 'chat_data': _json(d), 'allow_queries': False}}


# ---------- «Sozlamalar» (har bir xodim o'zi uchun) ----------
# Bo'limlar vidjet ichida almashadi (so'rovsiz); tanlov bosilganda `s:<xodim_id>:<bo'lim>:<qiymat>` so'rovi ketadi —
# bot uni matnli sozlamalardagi tugma bilan bir xil tekshiradi va saqlaydi (`bot_menyu.sozlama_tugma`).

SOZLAMA_HTML = _vidjet("""
.tb{display:flex;gap:6px;margin-top:12px}
.tb button{flex:1;padding:8px 4px;font-size:12px;color:#D4D7DE;background:rgba(14,19,30,.55);border-color:rgba(255,255,255,.14);border-radius:10px}
.tb .on{color:#171717;background:#F3BF70;border-color:#F3BF70}
.r{width:100%;justify-content:space-between;gap:12px;padding:10px 0;border:0;border-bottom:1px solid rgba(255,255,255,.08);border-radius:0;background:none;color:#F5F2EE;font-weight:600;text-align:left}
.r:last-of-type{border-bottom:0}
.sw{flex:none;width:38px;height:22px;border-radius:11px;background:rgba(255,255,255,.14);position:relative}
.sw i{position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:50%;background:#C9CCD4}
.sw.on{background:#62D4A3}
.sw.on i{left:19px;background:#fff}
.ch{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 4px}
.ch button{flex:1 0 40%;color:#F5F2EE;border-color:rgba(255,255,255,.16);background:rgba(14,19,30,.5);border-radius:12px;padding:10px 6px}
.ch .on,.op.on{color:#F3BF70;border-color:#F3BF70;background:rgba(243,191,112,.14)}
.op{display:block;width:100%;text-align:left;margin-top:8px;padding:12px;border-radius:14px;color:#F5F2EE;border-color:rgba(255,255,255,.16);background:rgba(14,19,30,.5)}
.op span{display:block;margin-top:4px;font-weight:500;font-size:12.5px;color:#C9CCD4}
.k{opacity:.55}
#x{min-height:17px}
""", """var D,T=0,M='',Z=0,B=['Turlar','Eslatma','Tinch vaqt','Maxfiylik'];
function sw(v,l,on){return'<button class=r data-v="'+v+'"><span>'+l+'</span><span class="sw'+(on?' on':'')+'"><i></i></span></button>'}
function ss(k){return(k<10?'0':'')+k+':00'}
function ch(s){var d;try{d=JSON.parse(s)}catch(x){}if(yo(d))return;D=d;dr()}
function dr(){var d=D,h=bs(e(d.s),'Sozlamalar','Bot xabarlari qachon va qanday kelsin');
h+='<div class=tb>'+B.map(function(n,i){return'<button data-t='+i+(i==T?' class=on':'')+'>'+n+'</button>'}).join('')+'</div><div class=g>';
if(T==0)h+='<div class=s>Qaysi xabarlar kelsin?</div>'+d.g.map(function(g){return sw('tur:'+g[0],e(g[1]),g[2])}).join('')+'<div class="s n">Qaror va pul bilan bog\\'liq xabarlar doim keladi.</div>';
if(T==1)h+='<div class=s>Kunlik eslatmalar (olib ketadi, qaytaradi, kechikdi) soat nechada kelsin?</div><div class=ch>'+d.h.map(function(k){return'<button data-v="esl:'+k+'"'+(k==d.e?' class=on':'')+'>'+ss(k)+'</button>'}).join('')+'</div>'+sw('esl:p','Primerkadan 1 soat oldin ham',d.p);
if(T==2){var t=d.t?d.t.join('-'):'0';h+='<div class=s>Shu oraliqda xabarlar yig\\'ilib turadi va keyin bitta bo\\'lib keladi.</div><div class=ch>'+[['0',"O'chiq"]].concat(d.tv.map(function(v){return[v.join('-'),v[0]+':00–'+ss(v[1])]})).map(function(v){return'<button data-v="tinch:'+v[0]+'"'+(v[0]==t?' class=on':'')+'>'+v[1]+'</button>'}).join('')+'</div>';
if(d.t)h+='<div class="s n">Tinch vaqtda ham darhol kelsin:</div>'+d.m.map(function(m){return sw('muhim:'+m[0],e(m[1]),!m[2])}).join('')}
if(T==3)h+='<div class=s>Telefon ekranida xabar qanday ko\\'rinsin?</div>'+[[0,"To'liq matn",'Xabar chatda darhol o\\'qiladi'],[1,'Yashirin','Chatda faqat «yangi xabar» chiqadi, mazmuni bosilganda ochiladi']].map(function(v){return'<button class="op'+((d.z?1:0)==v[0]?' on':'')+'" data-v="maxfiy:'+v[0]+'"><b>'+v[1]+'</b><span>'+v[2]+'</span></button>'}).join('');
a.innerHTML=h+'</div><div class="s n" id=x>'+M+'</div>'}
a.onclick=function(v){var b=v.target.closest('button');if(!b||Z)return;
if(b.hasAttribute('data-t')){T=+b.getAttribute('data-t');M='';dr();return}
v=b.getAttribute('data-v');if(!v||!W||!W.viewer||!D.x)return;Z=1;b.className+=' k';
W.request('s:'+D.x+':'+v).then(function(r){Z=0;M=r&&r.result?'✓ Saqlandi':'Saqlanmadi. Qayta bosing.';r&&r.result?ch(r.result):dr()},function(){Z=0;M='Saqlanmadi. Qayta bosing.';dr()})}
ch(W&&W.chatData);if(W){W.onEvent('chatDataChanged',function(){ch(W.chatData)});W.ready&&W.ready()}
""")


def sozlama_malumot(x):
    """Sozlamalar vidjeti holati: xodimning joriy tanlovlari va tanlash mumkin bo'lgan qiymatlar."""
    from .services import ESLATMA_SOATLARI, MUHIM_TOIFALAR, TINCH_VAQTLAR, XABAR_GURUHLARI, bot_soz
    s = bot_soz(x)
    ochirilgan = set(x.bot_ochirilgan or [])
    d = {'x': x.id, 's': x.salon.nomi[:40], 'e': s['eslatma'], 'h': list(ESLATMA_SOATLARI), 'p': s['primerka'],
         't': list(s['tinch']) if s['tinch'] else 0, 'tv': [list(v) for v in TINCH_VAQTLAR],
         'g': [[k, nom, k not in ochirilgan] for k, (nom, _, rollar) in XABAR_GURUHLARI.items() if x.rol in rollar],
         'm': [[k, nom, k in s['tinch_kutadi']] for k, (nom, _, rollar) in MUHIM_TOIFALAR.items() if x.rol in rollar],
         'z': s['maxfiy']}
    matn = _json(d)
    if len(matn.encode()) > MALUMOT_MAKS:  # juda uzun salon nomi — qisqartiriladi
        d['s'] = d['s'][:12]
        matn = _json(d)
    return matn


def sozlama_vidjeti(x, izoh_tugmalari=None):
    v = {'html': SOZLAMA_HTML, 'chat_data': sozlama_malumot(x), 'allow_queries': True}
    if izoh_tugmalari:
        v['reply_markup'] = {'inline_keyboard': izoh_tugmalari}
    return {'vidjet': v, 'zaxira': izoh_tugmalari}


# ---------- «To'lov» (rahbar): bank kartasi ko'rinishida ----------

_KARTA = re.compile(r'(?<!\d)(?:\d[ -]?){15}\d(?!\d)')
_ISM = re.compile(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻʼ'’`‘\-.]+")
_ISM_EMAS = {'karta', 'karta:', 'uzcard', 'humo', 'visa', 'mastercard', 'bank', 'raqam', 'raqami'}


def karta_ajrat(matn):
    """Ega kiritgan erkin to'lov matnidan: (karta raqami — faqat raqamlar, egasining ism-familiyasi, qolgan izoh).

    Ism — 2–4 so'zli, raqamsiz qator. Tanlash tartibi: «Karta egasi: …» / «Ism: …» deb belgilangan qator; bo'lmasa
    karta raqami turgan yoki unga qo'shni qator; boshqa joydagi qator («Click orqali to'lang») ism deb olinmaydi.
    Topilmasa '' — vidjet karta raqamini ismsiz ko'rsatadi.
    """
    matn = (matn or '').strip()
    m = _KARTA.search(matn)
    if not m:
        return '', '', matn
    raqam = re.sub(r'\D', '', m.group())
    karta_qatori = matn[:m.start()].count('\n')
    qatorlar = (matn[:m.start()] + matn[m.end():]).split('\n')  # karta raqami qatoridan olib tashlandi

    def toza(q):  # «Uzcard», «Karta» kabi so'zlarsiz
        return ' '.join(s for s in q.split() if s.lower().rstrip(':') not in _ISM_EMAS)

    def ismmi(q):
        sozlar = q.split()
        return 2 <= len(sozlar) <= 4 and all(_ISM.fullmatch(s) for s in sozlar)
    # ustuvorlik: belgilangan qator, karta qatori, keyingi qator, oldingi qator (bo'sh qatorlar o'tkazib yuboriladi —
    # ega ko'pincha karta raqami va ism orasiga bo'sh qator qo'yadi)
    keyingi = next((i for i in range(karta_qatori + 1, len(qatorlar)) if qatorlar[i].strip()), None)
    oldingi = next((i for i in range(karta_qatori - 1, -1, -1) if qatorlar[i].strip()), None)
    qoshni = {i: u for i, u in ((oldingi, 3), (keyingi, 2), (karta_qatori, 1)) if i is not None}
    tanlov = None  # (ustuvorlik, qator raqami, ism)
    for i, qator in enumerate(qatorlar):
        q = qator.strip(' ,;-—–')
        belgi, _, keyin = q.partition(':')
        if keyin and re.search(r'egasi|ism|f\.?i\.?sh|name', belgi, re.I) and ismmi(toza(keyin)):
            nomzod = (0, i, toza(keyin))
        elif i in qoshni and ismmi(toza(keyin if keyin else q)):
            nomzod = (qoshni[i], i, toza(keyin if keyin else q))
        else:
            continue
        if tanlov is None or nomzod[0] < tanlov[0]:
            tanlov = nomzod
    qolgan = []
    for i, qator in enumerate(qatorlar):
        q = qator.strip(' ,;-—–')
        if tanlov and i == tanlov[1]:
            continue
        if q and q.lower().rstrip(':') not in _ISM_EMAS:  # «Karta:», «Uzcard» — kartaning o'zida ko'rinadi
            qolgan.append(q)
    return raqam, tanlov[2] if tanlov else '', '\n'.join(qolgan)


TOLOV_HTML = _vidjet("""
.kr{position:relative;margin-top:12px;height:176px;box-sizing:border-box;padding:16px 18px;border-radius:18px;overflow:hidden;display:flex;flex-direction:column;background:radial-gradient(110% 90% at 100% 0,rgba(243,191,112,.34),transparent 55%),radial-gradient(80% 70% at 0 100%,rgba(121,169,242,.16),transparent 60%),linear-gradient(135deg,#2B2318,#151B29 55%,#0F1420);border:1px solid rgba(243,191,112,.55);box-shadow:inset 0 1px 0 rgba(255,255,255,.2),0 16px 30px rgba(0,0,0,.42)}
.kr .b{align-items:flex-start}
.kr .w{font-size:15px}
.kt{font:800 13px/1 system-ui,sans-serif;letter-spacing:.08em;color:#F6E7CC}
.cp{width:40px;height:30px;margin-top:14px;border-radius:7px;background:linear-gradient(135deg,#F6D9A0,#C99A52);border:1px solid rgba(0,0,0,.25)}
.kn{margin-top:auto;font:600 21px/1 ui-monospace,monospace;letter-spacing:.05em;white-space:nowrap}
.ke{margin-top:12px;font-size:10.5px;color:#C9CCD4}
.ke b{display:block;margin-top:2px;font-size:14px;letter-spacing:.06em;color:#F5F2EE;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tl{width:100%;margin-top:10px;padding:10px;color:#171717;background:#F3BF70;border-radius:14px;font-size:14px}
.q{display:flex;gap:8px;align-items:baseline;padding:3px 0;font-size:13px;color:#D4D7DE}
.q b{color:#F5F2EE}
.iz{white-space:pre-line;font-size:13px;line-height:18px;max-height:36px;overflow:hidden;color:#D4D7DE}
""", """function tp(k){return/^(8600|5614)/.test(k)?'UZCARD':/^9860/.test(k)?'HUMO':/^4/.test(k)?'VISA':/^(5[1-5]|2[2-7])/.test(k)?'MASTERCARD':''}
function ch(s){var d;try{d=JSON.parse(s)}catch(x){}if(yo(d))return;
var h=bs(e(d.s),'To\\'lov');
if(d.k)h+='<div class=kr><div class=b><span class=w>LIBOSA</span><span class=kt>'+tp(d.k)+'</span></div><div class=cp></div><div class=kn>'+d.k.replace(/(\\d{4})(?=\\d)/g,'$1 ')+'</div>'+(d.i?'<div class=ke>Karta egasi<b>'+e(d.i)+'</b></div>':'')+'</div><button class=tl id=k>'+ic('<rect x=9 y=9 width=13 height=13 rx=2 /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>')+'Karta raqamini nusxalash</button>';
h+='<div class=g>'+(d.w?'<div class=q><i class=d style="background:#F2C46D"></i><b>To\\'lovingiz tekshirilmoqda</b></div>':'')+'<div class=q><i class=d style="background:'+(d.r?'#F08089':'#62D4A3')+'"></i>'+e(d.o)+'</div>'+(d.n?'<div class=q><i class=d style="background:#79A9F2"></i>'+e(d.n)+'</div>':'')+(d.l?'<div class=q><i class=d style="background:#C9CCD4"></i>'+e(d.l)+'</div>':'')+(d.z?'<div class="iz n">'+e(d.z)+'</div>':'')+'</div>';
a.innerHTML=h;var k=document.getElementById('k');
if(k){if(!W||!W.copyText){k.style.display='none'}else k.onclick=function(){W.copyText(d.k);k.textContent='✓ Nusxalandi: '+d.k.replace(/(\\d{4})(?=\\d)/g,'$1 ')}}}
ch(W&&W.chatData);if(W){W.onEvent('chatDataChanged',function(){ch(W.chatData)});W.ready&&W.ready()}
""")


def tolov_malumot(x, malumot, oxirgi='', kutilmoqda=False):
    """To'lov vidjeti holati. `malumot` — ega kiritgan to'lov matni; karta topilmasa matnning o'zi ko'rsatiladi."""
    from apps.tenants.models import Salon

    from .bot_menyu import obuna_holati_matni
    from .services import som
    s = x.salon
    raqam, ism, qolgan = karta_ajrat(malumot)
    tarif = ''
    if s.tarif_id:
        tarif = f'Tarif: {s.tarif.nomi}' + (f' — oyiga {som(s.tarif.oylik_narx)}' if s.tarif.oylik_narx else '')
    d = {'x': x.id, 's': s.nomi[:40], 'o': obuna_holati_matni(s), 'r': s.holat == Salon.Holat.FAQAT_KORISH,
         'n': tarif[:80], 'k': raqam, 'i': ism[:40], 'z': qolgan[:300], 'w': kutilmoqda, 'l': oxirgi[:80]}
    matn = _json(d)
    while len(matn.encode()) > MALUMOT_MAKS and d['z']:  # izoh juda uzun — qisqartiriladi (karta va holat qoladi)
        d['z'] = d['z'][:len(d['z']) // 2].rstrip() + '…'
        matn = _json(d)
    return matn


def tolov_vidjeti(x, malumot, tugmalar, oxirgi='', kutilmoqda=False):
    return {'vidjet': {'html': TOLOV_HTML, 'chat_data': tolov_malumot(x, malumot, oxirgi, kutilmoqda),
                       'allow_queries': False, 'reply_markup': {'inline_keyboard': tugmalar}},
            'zaxira': tugmalar}


def namuna_sozlama():
    """Ega uchun: rahbar ko'radigan sozlamalar (standart qiymatlar; `x` = 0 — tanlov so'rovi yuborilmaydi)."""
    from .services import ESLATMA_SOATI, ESLATMA_SOATLARI, MUHIM_TOIFALAR, TINCH_VAQTLAR, XABAR_GURUHLARI
    d = {'x': 0, 's': 'Namuna salon', 'e': ESLATMA_SOATI, 'h': list(ESLATMA_SOATLARI), 'p': False,
         't': list(TINCH_VAQTLAR[0]), 'tv': [list(v) for v in TINCH_VAQTLAR],
         'g': [[k, nom, True] for k, (nom, _, _) in XABAR_GURUHLARI.items()],
         'm': [[k, nom, False] for k, (nom, _, _) in MUHIM_TOIFALAR.items()], 'z': False}
    return {'vidjet': {'html': SOZLAMA_HTML, 'chat_data': _json(d), 'allow_queries': False}}


def namuna_tolov():
    """Ega uchun: to'lov vidjeti uning o'zi kiritgan to'lov ma'lumoti bilan (kiritilmagan bo'lsa — namuna karta)."""
    from apps.tenants.models import platforma_sozlama
    malumot = platforma_sozlama().tolov_malumoti.strip() or '8600 0000 0000 0000\nIsm Familiya'
    raqam, ism, qolgan = karta_ajrat(malumot)
    d = {'x': 0, 's': 'Namuna salon', 'o': 'Obuna 26.12.2026 gacha — 30 kun qoldi', 'r': False,
         'n': "Tarif: Standart — oyiga 300 000 so'm", 'k': raqam, 'i': ism[:40], 'z': qolgan[:300], 'w': False,
         'l': ''}
    return {'vidjet': {'html': TOLOV_HTML, 'chat_data': _json(d), 'allow_queries': False}}


# ---------- yuborish va so'rovlar ----------

def yubor(chat_id, izoh, vidjet, token=None):
    """`sendWidget`. Telegram rad etsa `TelegramXatosi` — chaqiruvchi oddiy matnga qaytadi."""
    kw = {'_token': token} if token else {}
    return telegram.api('sendWidget', chat_id=chat_id, caption=izoh[:1024], **vidjet, **kw)


def sorov_ishla(wq, token=None):
    """`widget_query`: «Bugun» dagi «Yangilash» (`b:<xodim_id>`) yoki sozlama tanlovi (`s:<xodim_id>:<bo'lim>:<qiymat>`).

    Faqat o'sha xodimning o'z akkauntidan. Yangi holat so'ragan vidjetga javob bo'lib qaytadi va xabarning o'ziga ham
    yoziladi (keyin ochilganda yangi turadi). Rad etilsa — ma'lumotsiz javob (vidjet «saqlanmadi» deydi).
    """
    from . import bot_menyu
    kw = {'_token': token} if token else {}
    data = wq.get('data') or ''
    qismlar = data.split(':')
    kim = (wq.get('from') or {}).get('id')
    malumot = None
    if len(qismlar) == 2 and qismlar[0] == 'b' and qismlar[1].isdigit():
        x = Xodim.objects.filter(id=int(qismlar[1]), telegram_id=kim, faol=True,
                                 rol=Xodim.Rol.RAHBAR).select_related('salon').first()
        if x:
            malumot = bugun_malumot(x.salon, x.id)
    elif len(qismlar) == 4 and qismlar[0] == 's' and qismlar[1].isdigit():
        _, sahifa, _ = bot_menyu.sozlama_tugma(kim, data)
        if sahifa is not None:  # saqlandi (rad etilsa sahifa yo'q)
            x = Xodim.objects.select_related('salon').get(id=int(qismlar[1]))
            malumot = sozlama_malumot(x)
    if malumot is None:
        telegram.api('answerWidgetQuery', widget_query_id=wq['id'], **kw)
        return None
    telegram.api('answerWidgetQuery', widget_query_id=wq['id'], data=malumot, **kw)
    if wq.get('chat') and wq.get('message_id'):
        try:
            telegram.api('editMessageWidgetData', chat_id=wq['chat']['id'], message_id=wq['message_id'],
                         chat_data=malumot, **kw)
        except telegram.TelegramXatosi:  # «message is not modified» yoki limit — javob baribir yetib borgan
            pass
    return malumot
