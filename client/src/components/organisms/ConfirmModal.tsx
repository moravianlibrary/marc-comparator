import {
    Button,
    Divider,
    Modal,
    ModalBody,
    ModalFooter,
    ModalHeader,
    ModalVariant,
    Stack,
    StackItem,
} from "@patternfly/react-core";

interface ConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    isConfirmDisabled?: boolean;
    title?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    /** Highlighted block at the top (e.g. selected count). Visually distinct from body. */
    summary?: React.ReactNode;
    /** Optional settings/form section below the main body. */
    settings?: React.ReactNode;
    children: React.ReactNode;
}

const ConfirmModal = ({
    isOpen,
    onClose,
    onConfirm,
    isConfirmDisabled,
    title = "Confirm",
    confirmLabel = "Confirm",
    cancelLabel = "Cancel",
    summary,
    settings,
    children,
}: ConfirmModalProps) => {
    const bodyContent = (
        <Stack hasGutter>
            {summary != null && (
                <StackItem>
                    <div
                        className="pf-v5-u-p-md pf-v5-u-border-left-lg pf-v5-u-border-color-200-on-light pf-v5-u-background-color-200-on-light"
                        data-testid="confirm-modal-summary"
                    >
                        {summary}
                    </div>
                </StackItem>
            )}
            {children && (
                <StackItem>{children}</StackItem>
            )}
            {settings != null && (
                <>
                    <StackItem>
                        <Divider />
                    </StackItem>
                    <StackItem data-testid="confirm-modal-settings">
                        {settings}
                    </StackItem>
                </>
            )}
        </Stack>
    );

    return (
        <Modal
            variant={ModalVariant.small}
            isOpen={isOpen}
            onClose={onClose}
            onEscapePress={onClose}
            aria-labelledby="modal-with-dropdown"
            aria-describedby="modal-box-body-with-dropdown"
        >
            <ModalHeader title={title} labelId="modal-with-dropdown" />
            <ModalBody id="modal-box-body-with-dropdown">{bodyContent}</ModalBody>
            <ModalFooter>
                <Button
                    key="confirm"
                    variant="primary"
                    onClick={() => onConfirm()}
                    isDisabled={isConfirmDisabled}
                >
                    {confirmLabel}
                </Button>
                <Button key="cancel" variant="link" onClick={onClose}>
                    {cancelLabel}
                </Button>
            </ModalFooter>
        </Modal>
    );
};

export default ConfirmModal;
