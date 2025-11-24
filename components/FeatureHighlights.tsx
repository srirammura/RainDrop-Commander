"use client";

export default function FeatureHighlights() {
  const features = [
    {
      icon: "✅",
      title: "Curated",
      description:
        "Curated datasets ensure a quality foundation for your models, reducing noise and improving accuracy.",
      color: "green",
    },
    {
      icon: "🧠",
      title: "Fine-tuned",
      description:
        "Fine-tuned models deliver superior results by learning from your specific domain and use cases.",
      color: "purple",
    },
    {
      icon: "🏢",
      title: "Enterprise",
      description:
        "Built for enterprise scale with robust infrastructure, security, and compliance features.",
      color: "blue",
    },
    {
      icon: "⚡",
      title: "Fast-paced",
      description:
        "Fast-paced development cycles ensure rapid iteration and deployment of your AI solutions.",
      color: "yellow",
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-900 py-12">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8 text-gray-900 dark:text-white">
          BUILT FOR CUTTING-EDGE AI PRODUCTS
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6"
            >
              <div className="text-4xl mb-3">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

