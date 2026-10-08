import { VerifyEmail } from "./VerifyEmail";

export const metadata = {
  title: "Confirm your email",
  robots: { index: false, follow: false },
};

export default async function VerifyEmailPage({ searchParams }) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Confirm your email</h1>
      <VerifyEmail token={typeof token === "string" ? token : ""} />
    </div>
  );
}
