import {
    Button,
    Modal,
    ModalBody,
    ModalFooter,
    ModalHeader,
    ModalVariant,
} from "@patternfly/react-core";

interface ConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    isConfirmDisabled?: boolean;
    children: React.ReactNode;
}

const ConfirmModal = ({
    isOpen,
    onClose,
    onConfirm,
    isConfirmDisabled,
    children,
}: ConfirmModalProps) => {
    return (
        <Modal
            variant={ModalVariant.small}
            isOpen={isOpen}
            onClose={onClose}
            onEscapePress={onClose}
            aria-labelledby="modal-with-dropdown"
            aria-describedby="modal-box-body-with-dropdown"
        >
            <ModalHeader title="Dropdown modal" labelId="modal-with-dropdown" />
            <ModalBody id="modal-box-body-with-dropdown">{children}</ModalBody>
            <ModalFooter>
                <Button
                    key="confirm"
                    variant="primary"
                    onClick={() => onConfirm()}
                    isDisabled={isConfirmDisabled}
                >
                    Confirm
                </Button>
                <Button key="cancel" variant="link" onClick={onClose}>
                    Cancel
                </Button>
            </ModalFooter>
        </Modal>
    );
};

export default ConfirmModal;
