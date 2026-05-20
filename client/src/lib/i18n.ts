import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import HttpBackend from "i18next-http-backend";
import { z } from "zod";

z.config(z.locales.cs());

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    lng: "cs",
    fallbackLng: "cs",
    ns: [
      "common",
      "auth",
      "settings",
      "tasks",
      "access-control",
      "system",
      "records",
    ],
    defaultNS: "common",
    backend: {
      loadPath: "/locales/{{lng}}/{{ns}}.json",
    },
    interpolation: { escapeValue: false },
  });

export default i18n;
