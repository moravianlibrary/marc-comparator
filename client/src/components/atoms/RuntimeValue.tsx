import MonospaceValue from "./MonospaceValue";

interface RuntimeValueProps {
    startedAt: Date;
    finishedAt: Date | null;
}

const pad2 = (n: number) => String(n).padStart(2, " ");

const RuntimeValue = ({ startedAt, finishedAt }: RuntimeValueProps) => {
    const runTimeMs =
        (finishedAt ?? new Date()).getTime() - startedAt.getTime();
    const seconds = Math.floor((runTimeMs / 1000) % 60);
    const minutes = Math.floor((runTimeMs / (1000 * 60)) % 60);
    const hours = Math.floor(runTimeMs / (1000 * 60 * 60));

    let value = "";

    if (hours > 0) {
        value = `${hours}h ${pad2(minutes)}m ${pad2(seconds)}s`;
    } else if (minutes > 0) {
        value = `${minutes}m ${pad2(seconds)}s`;
    } else {
        value = `${seconds}s`;
    }

    return <MonospaceValue value={value} width={11} toRight />;
};

export default RuntimeValue;
