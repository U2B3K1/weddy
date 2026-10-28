// Reklama sahifasida g'ildirakni silliq aylantirish (Reklama.jsx) boshqaradi. Bo'lim o'z g'ildirak mantiqiga muhtoj bo'lsa
// (masalan, «Imkoniyatlar» slayderi: bitta harakat — bitta slayd), shu yerga tutqich qo'yadi: Reklama.jsx har hodisani
// avval tutqichga beradi, tutqich true qaytarsa — hodisa bo'limniki, sahifa o'zi aylanmaydi.
let tutqich = null

// Qaytgan funksiya tutqichni olib tashlaydi (useEffect tozalashi uchun)
export const tutqichQoy = (f) => { tutqich = f; return () => { if (tutqich === f) tutqich = null } }
export const tutqichga = (e) => !!tutqich?.(e)
