// Har faslning fon rasmi (public/kalendar/fasl-*.jpg): oltin chiziqli saroy manzarasi, Sana bloki orqasida xira turadi.
// Oylar faslga bog'langan: dekabr–fevral qish, mart–may bahor, iyun–avgust yoz, sentabr–noyabr kuz.
const OY_FASLI = ['qish', 'qish', 'bahor', 'bahor', 'bahor', 'yoz', 'yoz', 'yoz', 'kuz', 'kuz', 'kuz', 'qish']
export const MAVZULAR = OY_FASLI.map((fasl) => ({ fasl, rasm: `/kalendar/fasl-${fasl}.jpg` }))
