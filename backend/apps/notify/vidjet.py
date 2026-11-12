"""Telegram vidjetlari (Bot API 10.4): xabar ichida ishlaydigan kichik interfeys — sinov tariqasida rahbarning «Bugun» ekrani.

Vidjet — bitta HTML (kodi yuborilgach o'zgarmaydi) + bot o'zgartiradigan holat (`chat_data`, 1024 baytgacha JSON).
Cheklovlar (core.telegram.org/bots/widgets): tarmoq yo'q, faqat tizim shriftlari, matn kiritish yo'q, HTML 32 KB
(siqilganda 4 KB) gacha, faqat bot bilan shaxsiy suhbatda. Vidjetni tanimaydigan ilovada xabar izohi (caption)
ko'rinadi — shuning uchun izohga doim to'liq matnli hisobot yoziladi.

Ko'rinish loyiha uslubidan: to'q ko'k fon, tilla urg'u, shisha kartalar (frontend/src/yangi-dizayn.css tokenlari).
Sozlama: `PlatformaSozlama.bot_vidjet` (standart o'chiq) — ega botda `/vidjet` bilan namunani ko'rib, keyin yoqadi.
"""
import json

from django.utils import timezone

from apps.tenants.models import Xodim

from . import telegram

MALUMOT_MAKS = 1024  # chat_data chegarasi (bayt)

BUGUN_HTML = """<style>
html{background:#0D1320 radial-gradient(120% 80% at 100% 0,rgba(243,191,112,.16),transparent 60%)}
body{margin:0;color:#F4EFE7;font:14px/1.35 system-ui,sans-serif;padding:14px 14px 12px}
.b{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.l{font-size:11px;letter-spacing:.22em;color:#F3BF70;font-weight:600}
.s{font-size:12px;color:#A9B1BE;white-space:nowrap}
.h{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;text-align:right}
.k{margin-top:10px;padding:12px;border-radius:14px;background:rgba(255,255,255,.05);border:1px solid rgba(243,191,112,.22)}
.t{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums}
.t small{font-size:13px;font-weight:500;color:#A9B1BE}
.z{height:6px;border-radius:3px;background:rgba(255,255,255,.08);margin:10px 0 8px;overflow:hidden;display:flex}
.z i{display:block;height:100%}
.q{display:flex;justify-content:space-between;font-size:12.5px;color:#D4D7DE;padding:2px 0}
.q b{font-variant-numeric:tabular-nums;font-weight:600;color:#F4EFE7}
.d{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.u{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}
.u div{padding:10px 8px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08)}
.u b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
.u span{font-size:11.5px;color:#A9B1BE}
.o{margin-top:10px;display:flex;justify-content:space-between;align-items:center;gap:8px}
button{font:600 13px system-ui,sans-serif;color:#171717;background:#F3BF70;border:0;border-radius:10px;padding:8px 14px}
button:disabled{opacity:.55}
</style>
<div id=a></div>
<script>
var W=window.TelegramWidget,a=document.getElementById('a'),R=['#F3BF70','#7FA6E8','#6FCFB4','#C79BE8','#E88F8F'];
function f(n){return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')}
function e(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ch(s){var d;try{d=JSON.parse(s)}catch(x){}
if(!d){a.innerHTML='<div class=s>Ma\\'lumot yo\\'q. Menyuda «Bugun» ni qayta bosing.</div>';return}
var j=d.t||0,u=[['Naqd',d.n]].concat(d.u||[]).filter(function(p){return p[1]>0}),h='';
h+='<div class=b><span class=l>LIBOSA</span><span class="s h">'+e(d.s)+'</span><span class=s>'+e(d.d)+'</span></div>';
h+='<div class=k><div class=s>Bugungi tushum</div><div class=t>'+f(j)+' <small>so\\'m</small></div>';
if(u.length&&j>0){h+='<div class=z>'+u.map(function(p,i){return'<i style="width:'+(p[1]/j*100)+'%;background:'+R[i%5]+'"></i>'}).join('')+'</div>'+u.map(function(p,i){return'<div class=q><span><i class=d style="background:'+R[i%5]+'"></i>'+e(p[0])+'</span><b>'+f(p[1])+'</b></div>'}).join('')}
h+='</div><div class=u>'+[['Yangi bron',d.y],['Berildi',d.b],['Qaytdi',d.q]].map(function(p){return'<div><b>'+e(p[1])+'</b><span>'+p[0]+'</span></div>'}).join('')+'</div>';
h+='<div class=o><span class=s>'+(d.o?'<i class=d style="background:#6FCFB4"></i>Smena ochiq':d.f==null?'Bugun smena yopilmagan':'Kassa farqi: '+f(d.f)+' so\\'m')+' · '+e(d.v)+'</span><button id=y>Yangilash</button></div>';
a.innerHTML=h;var y=document.getElementById('y');
if(!W||!W.viewer||!d.x){y.style.display='none';return}
y.onclick=function(){y.disabled=true;y.textContent='…';W.request('b:'+d.x).then(function(r){ch(r&&r.result||W.chatData)},function(){y.disabled=false;y.textContent='Qayta urinish'})}}
ch(W&&W.chatData);if(W){W.onEvent('chatDataChanged',function(){ch(W.chatData)});W.ready&&W.ready()}
</script>"""


def bugun_malumot(salon, xodim_id=0, bugun=None):
    """«Bugun» vidjeti holati — ixcham JSON (kalitlar bir harfli: 1024 baytga sig'ishi kerak)."""
    from .management.commands.kunlik_hisobot import kunlik_raqamlar
    bugun = bugun or timezone.localdate()
    r = kunlik_raqamlar(salon, bugun)
    d = {'x': xodim_id, 's': salon.nomi[:40], 'd': f'{bugun:%d.%m.%Y}', 'v': f'{timezone.localtime():%H:%M}',
         't': r['tushum'], 'n': r['naqd'], 'u': [[nom[:16], s] for nom, s in r['naqdsiz']][:4],
         'y': r['yangi'], 'b': r['berilgan'], 'q': r['qaytgan'], 'f': r['farq'], 'o': r['ochiq']}
    matn = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    if len(matn.encode()) > MALUMOT_MAKS:  # juda uzun nomlar — to'lov usullari bo'limisiz
        d['u'] = []
        matn = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    return matn


def bugun_vidjeti(x):
    """Dispetcher uchun: `_javob_yubor` shu lug'atni ko'rsa `sendWidget` qiladi, bo'lmasa matnning o'zi ketadi."""
    return {'vidjet': {'html': BUGUN_HTML, 'chat_data': bugun_malumot(x.salon, x.id), 'allow_queries': True}}


NAMUNA = {'x': 0, 's': 'Namuna salon', 'd': '', 'v': '', 't': 4_850_000, 'n': 2_600_000,
          'u': [['Karta', 1_500_000], ["O'tkazma", 750_000]], 'y': 3, 'b': 2, 'q': 1, 'f': None, 'o': True}


def namuna_vidjeti():
    """Ega uchun: o'ylab topilgan raqamlar bilan ko'rinish namunasi (haqiqiy salon ma'lumoti emas)."""
    d = {**NAMUNA, 'd': f'{timezone.localdate():%d.%m.%Y}', 'v': f'{timezone.localtime():%H:%M}'}
    return {'vidjet': {'html': BUGUN_HTML, 'chat_data': json.dumps(d, ensure_ascii=False, separators=(',', ':')),
                       'allow_queries': False}}


def yubor(chat_id, izoh, vidjet, token=None):
    """`sendWidget`. Telegram rad etsa `TelegramXatosi` — chaqiruvchi oddiy matnga qaytadi."""
    kw = {'_token': token} if token else {}
    return telegram.api('sendWidget', chat_id=chat_id, caption=izoh[:1024], **vidjet, **kw)


def sorov_ishla(wq, token=None):
    """`widget_query`: vidjetdagi «Yangilash» (`b:<xodim_id>`). Faqat o'sha xodimning o'z akkauntidan.

    Yangi holat so'ragan vidjetga javob bo'lib qaytadi va xabarning o'ziga ham yoziladi (keyin ochilganda yangi turadi).
    """
    kw = {'_token': token} if token else {}
    qismlar = (wq.get('data') or '').split(':')
    x = None
    if len(qismlar) == 2 and qismlar[0] == 'b' and qismlar[1].isdigit():
        x = Xodim.objects.filter(id=int(qismlar[1]), telegram_id=(wq.get('from') or {}).get('id'), faol=True,
                                 rol=Xodim.Rol.RAHBAR).select_related('salon').first()
    if not x:
        telegram.api('answerWidgetQuery', widget_query_id=wq['id'], **kw)
        return None
    malumot = bugun_malumot(x.salon, x.id)
    telegram.api('answerWidgetQuery', widget_query_id=wq['id'], data=malumot, **kw)
    if wq.get('chat') and wq.get('message_id'):
        try:
            telegram.api('editMessageWidgetData', chat_id=wq['chat']['id'], message_id=wq['message_id'],
                         chat_data=malumot, **kw)
        except telegram.TelegramXatosi:  # «message is not modified» yoki limit — javob baribir yetib borgan
            pass
    return malumot
