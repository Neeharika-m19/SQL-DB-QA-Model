import React from 'react';

export default function ChatLayout({ children, footer }) {
  return (
    <div className="flex flex-col h-screen">
      <header className="px-4 py-2 bg-white shadow">DB-LLM Chat</header>
      <main className="flex-1 overflow-auto p-4 space-y-2">{children}</main>
      <footer className="px-4 py-2 bg-white shadow">{footer}</footer>
    </div>
  );
}
