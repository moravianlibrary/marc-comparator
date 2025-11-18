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

const LoginDataSchema = z.object({
    username: z.email({ message: "Must be a valid email" }),
    password: z.string().min(1, { message: "Password is required" }),
});
type LoginData = z.infer<typeof LoginDataSchema>;

const AuthPage = (): ReactElement => {
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
        console.log("Login data validation result:", result);

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
            loginTitle="Log in to your account"
            loginSubtitle="Enter your credentials."
            brandImgSrc="marcomparator-logo-dark-text-transparent.png"
            brandImgAlt="MarcComparator logo"
            textContent="This is placeholder text only. Use this area to place any information or introductory message about your application that may be relevant to users."
            signUpForAccountMessage={
                <LoginMainFooterBandItem>
                    Need an account?{" "}
                    <Button variant="link" onClick={() => navigate("/signup")}>
                        Sign up.
                    </Button>
                </LoginMainFooterBandItem>
            }
        >
            <LoginForm
                usernameLabel="Email"
                usernameValue={loginData.username}
                onChangeUsername={(_, value: string) =>
                    setLoginData({ ...loginData, username: value })
                }
                isValidUsername={!errors.username}
                passwordLabel="Password"
                passwordValue={loginData.password}
                onChangePassword={(_, value: string) =>
                    setLoginData({ ...loginData, password: value })
                }
                isValidPassword={!errors.password}
                showHelperText={!!(errors.username || errors.password)}
                helperText={
                    !!(errors.username && errors.password)
                        ? "Invalid login credentials."
                        : errors.username ||
                          errors.password ||
                          "Invalid login credentials."
                }
                helperTextIcon={<ExclamationCircleIcon />}
                onLoginButtonClick={handleSubmit}
                loginButtonLabel="Log in"
                isLoginButtonDisabled={isPending}
            />
        </LoginPage>
    );
};

export default AuthPage;
