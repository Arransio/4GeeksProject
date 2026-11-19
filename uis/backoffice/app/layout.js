export const metadata = {
  title: "HealthCore Operations | Backoffice",
  description: "Backoffice interno de HealthCore",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}