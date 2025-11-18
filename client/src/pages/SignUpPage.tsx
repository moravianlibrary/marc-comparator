import {
    Button,
    LoginMainFooterBandItem,
    LoginPage,
} from "@patternfly/react-core";
import { useEffect, type ReactElement } from "react";
import SignUpForm from "../components/organisms/SignUpForm";
import { useSignUp } from "../hooks/useAuth";
import { useNavigate } from "react-router";

const SignUpPage = (): ReactElement => {
    const { mutate: signUp, isPending, isSuccess } = useSignUp();
    const navigate = useNavigate();

    useEffect(() => {
        if (isSuccess) {
            navigate("/login");
        }
    }, [isSuccess]);

    return (
        <LoginPage
            loginTitle="Register"
            loginSubtitle="Enter your credentials."
            brandImgSrc="marcomparator-logo-dark-text-transparent.png"
            brandImgAlt="MarcComparator logo"
            signUpForAccountMessage={
                <LoginMainFooterBandItem>
                    Already have an account?{" "}
                    <Button variant="link" onClick={() => navigate("/login")}>
                        Log in.
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
