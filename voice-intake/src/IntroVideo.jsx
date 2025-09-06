export default function IntroVideo({ onContinue }) {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-black text-white">
      <video
        className="w-full max-w-lg rounded-lg"
        autoPlay
        muted
        onEnded={onContinue}
      >
        <source src="/claim.mp4" type="video/mp4" />
      </video>
      <button
        onClick={onContinue}
        className="mt-4 px-4 py-2 bg-blue-500 rounded-lg"
      >
        Skip Intro
      </button>
    </div>
  );
}

