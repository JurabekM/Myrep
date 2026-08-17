import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col">
      <ChatWindow module="chat" />
    </div>
  );
}
