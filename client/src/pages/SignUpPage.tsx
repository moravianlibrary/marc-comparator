import {
    Button,
    LoginMainFooterBandItem,
    LoginPage,
} from "@patternfly/react-core";
import { useEffect, type ReactElement } from "react";
import SignUpForm from "../components/organisms/SignUpForm";
import { useSignUp } from "../hooks/useAuth";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

const SignUpPage = (): ReactElement => {
    const { t } = useTranslation();
    const { mutate: signUp, isPending, isSuccess } = useSignUp();
    const navigate = useNavigate();

    useEffect(() => {
        if (isSuccess) {
            navigate("/login");
        }
    }, [isSuccess]);

    return (
        <LoginPage
            loginTitle={t("auth:signup.title")}
            loginSubtitle={t("auth:signup.subtitle")}
            brandImgSrc="marcomparator-logo-dark-text-transparent.png"
            brandImgAlt="MarcComparator logo"
            textContent={t("auth:about-app")}
            signUpForAccountMessage={
                <LoginMainFooterBandItem>
                    {`${t("auth:signup.already-have-account-message")} `}
                    <Button variant="link" onClick={() => navigate("/login")}>
                        {t("auth:signup.already-have-account-link")}
                    </Button>
                </LoginMainFooterBandItem>
            }
        >
            <SignUpForm
                onSubmit={(data) => signUp(data)}
                isPending={isPending}
            />
        </LoginPage>
    );
};

export default SignUpPage;
