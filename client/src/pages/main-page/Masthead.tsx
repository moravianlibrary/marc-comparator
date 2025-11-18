import {
    Masthead,
    MastheadContent,
    MastheadMain,
    MastheadToggle,
    PageToggleButton,
} from "@patternfly/react-core";
import type { ReactElement } from "react";
import MainPageMastheadToolbar from "./MastheadToolbar";

const MainPageMasthead = (): ReactElement => {
    return (
        <Masthead>
            <MastheadMain>
                <MastheadToggle>
                    <PageToggleButton
                        isHamburgerButton
                        aria-label="Global navigation"
                    />
                </MastheadToggle>
                {/* <MastheadBrand>
                    <MastheadLogo>
                        <Brand
                            src={pfLogo}
                            alt="PatternFly"
                            heights={{ default: "36px" }}
                        />
                    </MastheadLogo>
                </MastheadBrand> */}
            </MastheadMain>
            <MastheadContent>
                <MainPageMastheadToolbar />
            </MastheadContent>
        </Masthead>
    );
};

export default MainPageMasthead;
