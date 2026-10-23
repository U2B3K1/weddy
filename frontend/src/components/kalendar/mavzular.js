// Har oyning fon fotosi (public/kalendar/NN.jpg) va urg'u rangi.
// Fotolar Unsplash'dan (bepul litsenziya), manba ID lari izohda.
// parda — fon ustidagi qorong'i qatlam kuchi: och fotolarda matn o'qilishi uchun kattaroq.
export const MAVZULAR = [
  { nomi: 'Qish · qorli o\'rmon', urgu: '#3E6A93', parda: 0.85 }, // photo-1642638966040-547114e05439
  { nomi: 'Qish · ayoz naqshlari', urgu: '#3F78B5', parda: 0.65 }, // photo-1671935605022-145ca432ef18
  { nomi: 'Bahor · o\'rik gullari', urgu: '#2F78B8', parda: 0.5 }, // photo-1709629105000-76b9584ba556
  { nomi: 'Bahor · gilos gullari', urgu: '#C2577A', parda: 0.5 }, // photo-1538943186303-104afadcbb16
  { nomi: 'Bahor · pionlar', urgu: '#B83E6A', parda: 0.42 }, // photo-1656056971530-641871b3bce3
  { nomi: 'Yoz · atirgullar', urgu: '#C23F5E', parda: 0.42 }, // photo-1644248423203-80e317d78aee
  { nomi: 'Yoz · kungaboqarlar', urgu: '#C9811C', parda: 0.48 }, // photo-1764484636506-cf6398999671
  { nomi: 'Yoz · lavanda', urgu: '#7A55B0', parda: 0.45 }, // photo-1769799188364-41f53cf8a7e4
  { nomi: 'Kuz · qizil rezavorlar', urgu: '#C4422D', parda: 0.45 }, // photo-1603020531733-3d148b4d4dd0
  { nomi: 'Kuz · zarang barglari', urgu: '#C0392B', parda: 0.42 }, // photo-1633719910794-2d65a3a4a929
  { nomi: 'Kuz · qirovli xazon', urgu: '#9A5A30', parda: 0.5 }, // photo-1666936052545-550714b6fcb6
  { nomi: 'Qish · yangi yil', urgu: '#B8322F', parda: 0.45 }, // photo-1575401744434-8e752e238768
].map((m, i) => ({ ...m, rasm: `/kalendar/${String(i + 1).padStart(2, '0')}.jpg` }))
