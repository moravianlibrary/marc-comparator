import { Button, type ButtonProps } from "@patternfly/react-core";
import { useNavigate } from "react-router";

interface NavigateButtonProps extends Omit<ButtonProps, "onClick"> {
    to: string;
}

const NavigateButton = ({ to, ...buttonProps }: NavigateButtonProps) => {
    const navigate = useNavigate();

    return <Button {...buttonProps} onClick={() => navigate(to)} />;
};

export default NavigateButton;
