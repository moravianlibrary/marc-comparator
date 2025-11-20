interface MonospaceValueProps {
    value: string;
    bold?: boolean;
    width?: number;
    toRight?: boolean;
}

const MonospaceValue = ({
    value,
    bold,
    width,
    toRight,
}: MonospaceValueProps) => {
    return (
        <span
            style={{
                fontFamily: "monospace",
                whiteSpace: "pre",
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
