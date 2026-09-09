import HeroSection from "@/components/hero/HeroSection";
import HowItWorksSection from "@/components/sections/HowItWorksSection";
import NVDAExampleSection from "@/components/sections/NVDAExampleSection";
import ExposureGraphPreview from "@/components/sections/ExposureGraphPreview";
import PortfolioPreview from "@/components/sections/PortfolioPreview";
import TokenUtilitySection from "@/components/sections/TokenUtilitySection";
import MethodologySection from "@/components/sections/MethodologySection";
import FinalCTASection from "@/components/sections/FinalCTASection";

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <HowItWorksSection />
      <NVDAExampleSection />
      <ExposureGraphPreview />
      <PortfolioPreview />
      <TokenUtilitySection />
      <MethodologySection />
      <FinalCTASection />
    </>
  );
}
