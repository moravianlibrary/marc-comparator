import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { AppLogo } from "@/components/app-logo";
import { useLogin, useOidcEnabled } from "@/hooks/use-auth";
import { loginSchema, type LoginFormValues } from "./schemas";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

export function LoginPage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get("redirect") || "/";
  const login = useLogin();
  const { data: oidc } = useOidcEnabled();
  const [emailFormOpen, setEmailFormOpen] = useState(false);

  const isOidcDefault = oidc?.enabled && oidc?.default;

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    try {
      await login.mutateAsync(values);
      navigate(redirectTo, { replace: true });
    } catch {
      form.setError("root", {
        message: t("login.form.invalid-credentials"),
      });
    }
  }

  const oidcButton = oidc?.enabled && (
    <Button
      variant={isOidcDefault ? "default" : "outline"}
      className="w-full"
      asChild
    >
      <a href={`/api/auth/oidc/login?redirect=${encodeURIComponent(redirectTo)}`}>
        {t("login.oidc-button")}
      </a>
    </Button>
  );

  const emailForm = (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        {form.formState.errors.root && (
          <p className="text-sm text-destructive text-center">
            {form.formState.errors.root.message}
          </p>
        )}
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("login.form.email")}</FormLabel>
              <FormControl>
                <Input type="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("login.form.password")}</FormLabel>
              <FormControl>
                <Input type="password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button
          type="submit"
          className="w-full"
          variant={isOidcDefault ? "outline" : "default"}
          disabled={login.isPending}
        >
          {t("login.form.submit")}
        </Button>
      </form>
    </Form>
  );

  const orSeparator = (
    <div className="relative my-4">
      <Separator />
      <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
        {t("login.or")}
      </span>
    </div>
  );

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-muted/50 animate-fade-in">
      <ThemeToggle className="absolute right-4 top-4" />
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <AppLogo />
          <CardTitle>{t("login.title")}</CardTitle>
          <CardDescription>{t("login.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          {isOidcDefault ? (
            <>
              {oidcButton}
              {orSeparator}
              <Collapsible open={emailFormOpen} onOpenChange={setEmailFormOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="w-full text-muted-foreground">
                    {t("login.email-login")}
                    <ChevronDown className={`ml-2 h-4 w-4 transition-transform ${emailFormOpen ? "rotate-180" : ""}`} />
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-4">
                  {emailForm}
                </CollapsibleContent>
              </Collapsible>
            </>
          ) : (
            <>
              {emailForm}
              {oidc?.enabled && (
                <>
                  {orSeparator}
                  {oidcButton}
                </>
              )}
            </>
          )}
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {t("login.sign-up-message")}{" "}
            <Link to="/signup" className="text-primary hover:underline">
              {t("login.sign-up-link")}
            </Link>
          </p>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            {t("about-app")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
