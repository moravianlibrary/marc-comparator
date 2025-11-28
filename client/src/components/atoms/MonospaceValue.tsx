interface MonospaceValueProps {
    value: string;
    bold?: boolean;
    width?: number;
    toRight?: boolean;
    allowWrap?: boolean;
}

const MonospaceValue = ({
    value,
    bold,
    width,
    toRight,
    allowWrap,
}: MonospaceValueProps) => {
    return (
        <span
            style={{
                fontFamily: "monospace",
                whiteSpace: allowWrap ? "pre-wrap" : "pre",
                fontWeight: bold ? "bold" : "normal",
                width: width ? `${width}ch` : "auto",
                display: "inline-block",
                textAlign: toRight ? "right" : "left",
            }}
        >
            {value}
        </span>
    );
};

export default MonospaceValue;
