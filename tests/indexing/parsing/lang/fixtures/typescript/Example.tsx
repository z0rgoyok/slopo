type GreetingProps = { name: string };

export function Greeting({ name }: GreetingProps) {
  return <strong>Hello, {name}!</strong>;
}

export const Button = ({ label }: { label: string }) => (
  <button onClick={() => alert(label)}>{label}</button>
);
