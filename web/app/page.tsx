import HeroSection from "@/components/hero/HeroSection";
import HowItWorksSection from "@/components/sections/HowItWorksSection";
import NVDAExampleSection from "@/components/sections/NVDAExampleSection";
import ExposureGraphPreview from "@/components/sections/ExposureGraphPreview";
import PortfolioPreview from "@/components/sections/PortfolioPreview";
import DeltaUtilitySection from "@/components/sections/DeltaUtilitySection";
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
      <DeltaUtilitySection />
      <MethodologySection />
      <FinalCTASection />
    </>
  );
}
