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

// Override zod error messages with i18next translations
z.config({
  customError: (issue) => {
    const t = i18n.t.bind(i18n);

    if (issue.code === "too_small") {
      if (issue.origin === "string") {
        if (issue.minimum === 1) return t("validation.required");
        return t("validation.string-min", { min: issue.minimum });
      }
      if (issue.origin === "array") {
        return t("validation.array-min", { min: issue.minimum });
      }
      if (issue.origin === "number") {
        return t("validation.number-min", { min: issue.minimum });
      }
    }

    if (issue.code === "too_big") {
      if (issue.origin === "string") {
        return t("validation.string-max", { max: issue.maximum });
      }
      if (issue.origin === "number") {
        return t("validation.number-max", { max: issue.maximum });
      }
    }

    if (issue.code === "invalid_format") {
      if (issue.format === "email") return t("validation.email");
      if (issue.format === "url") return t("validation.url");
    }

    return undefined;
  },
});

export default i18n;
