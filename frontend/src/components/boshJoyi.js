import { createContext } from 'react'

// Bo'lim boshidagi joylar (App beradi): sarlavha ostidagi xulosa va tablar qatorining o'ngidagi tugma — BoshJoy.jsx;
// sozlamaYon — keng ekranda chap paneldagi Sozlama bo'limlari ro'yxati joyi
export const BoshJoyi = createContext({ xulosa: null, amal: null, sozlamaYon: null })
