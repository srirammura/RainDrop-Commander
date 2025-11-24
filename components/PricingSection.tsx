"use client";

export default function PricingSection() {
  const plans = [
    {
      name: "STARTER",
      badge: "Free forever",
      badgeColor: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
      features: [
        "Projects",
        "Users",
        "Data Storage",
        "API Access",
      ],
    },
    {
      name: "PRO",
      badge: null,
      badgeColor: "",
      features: [
        "Projects",
        "Users",
        "Data Storage",
        "API Access",
        "Advanced Analytics",
        "Priority Support",
      ],
    },
    {
      name: "ENTERPRISE",
      badge: null,
      badgeColor: "",
      features: [
        "Custom Projects",
        "Unlimited Users",
        "Dedicated Data Storage",
        "Premium API Access",
        "Enterprise Analytics",
        "24/7 Support",
        "SLAs",
      ],
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-900 py-12">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8 text-gray-900 dark:text-white">
          PRICING
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan, index) => (
            <div
              key={index}
              className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6"
            >
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                  {plan.name}
                </h3>
                {plan.badge && (
                  <span
                    className={`inline-block px-2 py-1 text-xs font-semibold rounded ${plan.badgeColor}`}
                  >
                    {plan.badge}
                  </span>
                )}
              </div>
              <ul className="space-y-2">
                {plan.features.map((feature, fIndex) => (
                  <li
                    key={fIndex}
                    className="text-sm text-gray-600 dark:text-gray-400"
                  >
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

