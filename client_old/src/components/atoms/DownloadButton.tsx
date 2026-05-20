import { Button, type ButtonProps } from "@patternfly/react-core";

interface DownloadButtonProps extends Omit<ButtonProps, "onClick"> {
    download: () => void | Promise<void>;
}

const DownloadButton = ({ download, ...buttonProps }: DownloadButtonProps) => {
    return <Button {...buttonProps} onClick={() => download()} />;
};

export default DownloadButton;
