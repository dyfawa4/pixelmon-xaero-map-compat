package xaero.pixelmon;

import java.lang.reflect.Field;
import net.minecraft.client.Minecraft;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.common.ForgeConfigSpec;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.registries.ForgeRegistries;

/** Separate the two compasses' otherwise identical default HUD positions. */
public final class CompassHud {
    private CompassHud() {}
    private static boolean item(ItemStack stack,String namespace) {
        ResourceLocation id=ForgeRegistries.ITEMS.getKey(stack.func_77973_b());
        return id!=null&&id.func_110624_b().equals(namespace);
    }
    private static Object option(Object config,String name)throws ReflectiveOperationException {
        Field field=config.getClass().getField(name);
        return ((ForgeConfigSpec.ConfigValue<?>)field.get(config)).get();
    }
    public static int natureYOffset(int original) {
        var player=Minecraft.func_71410_x().field_71439_g;
        if(player==null||!ModList.get().isLoaded("explorerscompass")||!ModList.get().isLoaded("naturescompass"))return original;
        ItemStack main=player.func_184614_ca(),off=player.func_184592_cb();
        ItemStack explorer=item(main,"explorerscompass")?main:item(off,"explorerscompass")?off:null;
        if(explorer==null||!(item(main,"naturescompass")||item(off,"naturescompass")))return original;
        if(!explorer.func_77942_o()||explorer.func_77978_p().func_74762_e("State")==0)return original;
        try {
            Object ec=Class.forName("com.chaosthedude.explorerscompass.config.ConfigHandler").getField("CLIENT").get(null);
            Object nc=Class.forName("com.chaosthedude.naturescompass.config.ConfigHandler").getField("CLIENT").get(null);
            String es=String.valueOf(option(ec,"overlaySide")),ns=String.valueOf(option(nc,"overlaySide"));
            int e=((Number)option(ec,"overlayLineOffset")).intValue(),n=((Number)option(nc,"overlayLineOffset")).intValue();
            if(es.equals(ns)&&n<=e+10&&e<=n+10)return original+Math.max(0,e+12-n)*9;
        } catch(ReflectiveOperationException | LinkageError ignored) {
            // Optional compass versions with different config APIs keep their native layout.
        }
        return original;
    }
}
