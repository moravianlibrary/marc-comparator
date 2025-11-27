import { useEffect, useState, type ReactElement } from "react";
import {
    Button,
    LoginForm,
    LoginMainFooterBandItem,
    LoginPage,
} from "@patternfly/react-core";
import { useLogin } from "../hooks/useAuth";
import { ExclamationCircleIcon } from "@patternfly/react-icons";
import { z } from "zod";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

const LoginDataSchema = z.object({
    username: z.email({ message: "Must be a valid email" }),
    password: z.string().min(1, { message: "Password is required" }),
});
type LoginData = z.infer<typeof LoginDataSchema>;

const AuthPage = (): ReactElement => {
    const { t } = useTranslation();
    const { mutate: login, isSuccess, isPending } = useLogin();
    const navigate = useNavigate();

    const [loginData, setLoginData] = useState<LoginData>({
        username: "",
        password: "",
    });
    const [errors, setErrors] = useState<
        Partial<Record<keyof LoginData, string>>
    >({});

    const redirectUrl = new URLSearchParams(window.location.search).get(
        "redirect"
    );

    useEffect(() => {
        if (isSuccess) {
            navigate(redirectUrl ?? "/");
        }
    }, [isSuccess, redirectUrl]);

    const handleSubmit = (
        event: React.MouseEvent<HTMLButtonElement, MouseEvent>
    ): void => {
        event.preventDefault();

        const result = LoginDataSchema.safeParse(loginData);

        if (!result.success) {
            const errorTree = z.treeifyError(result.error);

            const fieldErrors: Partial<Record<keyof LoginData, string>> = {};

            if (errorTree?.properties?.username?.errors?.length) {
                fieldErrors.username = errorTree.properties.username.errors[0];
            }

            if (errorTree?.properties?.password?.errors?.length) {
                fieldErrors.password = errorTree.properties.password.errors[0];
            }

            setErrors(fieldErrors);
            return;
        }

        setErrors({});
        login(loginData);
    };

    return (
        <LoginPage
            loginTitle={t("auth:login.title")}
            loginSubtitle={t("auth:login.subtitle")}
            brandImgSrc="marcomparator-logo-dark-text-transparent.png"
            brandImgAlt="MarcComparator logo"
            textContent={t("auth:about-app")}
            signUpForAccountMessage={
                <LoginMainFooterBandItem>
                    {`${t("auth:login.sign-up-for-account-message")} `}
                    <Button variant="link" onClick={() => navigate("/signup")}>
                        {t("auth:login.sign-up-link")}
                    </Button>
                </LoginMainFooterBandItem>
            }
        >
            <LoginForm
                usernameLabel={t("auth:login.form.username")}
                usernameValue={loginData.username}
                onChangeUsername={(_, value: string) =>
                    setLoginData({ ...loginData, username: value })
                }
                isValidUsername={!errors.username}
                passwordLabel={t("auth:login.form.password")}
                passwordValue={loginData.password}
                onChangePassword={(_, value: string) =>
                    setLoginData({ ...loginData, password: value })
                }
                isValidPassword={!errors.password}
                showHelperText={!!(errors.username || errors.password)}
                helperText={
                    !!(errors.username && errors.password)
                        ? t("auth:login.form.invalid-login-credentials")
                        : errors.username ||
                          errors.password ||
                          t("auth:login.form.invalid-login-credentials")
                }
                helperTextIcon={<ExclamationCircleIcon />}
                onLoginButtonClick={handleSubmit}
                loginButtonLabel={t("auth:login.form.login-button")}
                isLoginButtonDisabled={isPending}
            />
        </LoginPage>
    );
};

export default AuthPage;
