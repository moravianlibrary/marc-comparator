import { useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { AxiosError } from "axios";
import { ThemeToggle } from "@/components/theme-toggle";
import { AppLogo } from "@/components/app-logo";
import { useSignUp } from "@/hooks/use-auth";
import { signupSchema, type SignupFormValues } from "./schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

export function SignupPage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const signUp = useSignUp();
  const form = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      password: "",
      confirm_password: "",
    },
  });

  async function onSubmit(values: SignupFormValues) {
    try {
      await signUp.mutateAsync({
        email: values.email,
        first_name: values.first_name,
        last_name: values.last_name,
        password: values.password,
      });
      navigate("/login", { replace: true });
    } catch (error) {
      const detail =
        error instanceof AxiosError
          ? error.response?.data?.detail
          : undefined;
      form.setError("root", {
        message: detail ?? t("common:error"),
      });
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-muted/50">
      <ThemeToggle className="absolute right-4 top-4" />
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <AppLogo />
          <CardTitle>{t("signup.title")}</CardTitle>
          <CardDescription>{t("signup.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
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
                    <FormLabel>{t("signup.form.email")}</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("signup.form.first-name")}</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("signup.form.last-name")}</FormLabel>
                    <FormControl>
                      <Input {...field} />
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
                    <FormLabel>{t("signup.form.password")}</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("signup.form.confirm-password")}</FormLabel>
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
                disabled={signUp.isPending}
              >
                {t("signup.form.submit")}
              </Button>
            </form>
          </Form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            {t("signup.login-message")}{" "}
            <Link to="/login" className="text-primary hover:underline">
              {t("signup.login-link")}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
