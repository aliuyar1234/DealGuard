export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth pages have no shell/sidebar - just centered content
  return <>{children}</>;
}
