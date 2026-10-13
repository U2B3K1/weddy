import { BELGI_D } from '../pages/ezazBelgi'

// Ilova shapkasi. Telefonda (767px gacha) bosh sahifadagidek: chapda «menyu» tugmasi va logo, o'ngda — children;
// menyu tugmasi chapdan chiqadigan navni (.pastki) ochadi. Keng ekranda nav doim chap panelda turadi, shuning uchun
// tugma va logo yashirin — faqat children ko'rinadi.
export default function Shapka({ ochiq, onMenyu, children }) {
  return (
    <header className="yuqori">
      <button type="button" className="shapka-menyu" aria-label={ochiq ? 'Menyuni yopish' : 'Menyu'} aria-expanded={ochiq} onClick={onMenyu}>
        <i /><i /><i />
      </button>
      <span className="ilova-logo">
        <svg viewBox="-60 -40 640 640" aria-hidden="true"><path d={BELGI_D} fill="currentColor" /></svg>LIBOSA
      </span>
      <div className="shapka-ong">{children}</div>
    </header>
  )
}
