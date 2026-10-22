import { Brand } from "./Layout.jsx";

export default function PublicShell({ children, wide }) {
  return (
    <div className="public">
      <div className={wide ? "public-inner wide" : "public-inner"}>
        <div className="public-brand">
          <Brand />
        </div>
        {children}
      </div>
    </div>
  );
}