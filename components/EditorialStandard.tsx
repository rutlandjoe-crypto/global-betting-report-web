export default function EditorialStandard() {
  return (
    <div className="mt-10">
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 shadow-md">
        <h2 className="text-xl font-bold text-white mb-4 tracking-wide">
          GSR Network Editorial Standard
        </h2>

        <p className="text-sm text-neutral-400 mb-4">
          We believe AI should support journalism—not replace it.
        </p>

        <ul className="space-y-2 text-sm text-neutral-300">
          <li>• No AI-written stories</li>
          <li>• AI used for data, signals, and structure only</li>
          <li>• Final journalism always human-driven</li>
        </ul>
      </div>
    </div>
  );
}