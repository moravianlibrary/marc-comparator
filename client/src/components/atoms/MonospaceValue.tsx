interface MonospaceValueProps {
    value: string;
}

const MonospaceValue = ({ value }: MonospaceValueProps) => {
    return (
        <span
            style={{
                fontFamily: "monospace",
                whiteSpace: "nowrap",
            }}
        >
            {value}
        </span>
    );
};

export default MonospaceValue;
