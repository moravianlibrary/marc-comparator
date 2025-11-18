import { Label } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import type { AuthorityLink } from "../../models/api/responses/authority_link";

interface AuthorityLinkLabelProps {
    recordId: string;
    authorityLink: AuthorityLink;
    key?: number | string;
}

const AuthorityLinkLabel = ({
    recordId,
    authorityLink: { base },
    key,
}: AuthorityLinkLabelProps): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
            key={key}
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=authority_records&authorityLinks.base=${base}`
                )
            }
        >
            {base}
        </Label>
    );
};

export default AuthorityLinkLabel;
