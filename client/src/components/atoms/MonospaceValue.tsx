interface MonospaceValueProps {
    value: string;
    bold?: boolean;
}

const MonospaceValue = ({ value, bold }: MonospaceValueProps) => {
    return (
        <span
            style={{
                fontFamily: "monospace",
                whiteSpace: "nowrap",
                fontWeight: bold ? "bold" : "normal",
            }}
        >
            {value}
        </span>
    );
};

export default MonospaceValue;
