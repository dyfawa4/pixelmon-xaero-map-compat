package mapcompat.qa;

import com.pixelmonmod.pixelmon.api.pokemon.Pokemon;
import com.pixelmonmod.pixelmon.api.pokemon.PokemonFactory;
import com.pixelmonmod.pixelmon.api.registries.PixelmonSpecies;
import com.pixelmonmod.pixelmon.api.storage.StorageProxy;
import com.pixelmonmod.pixelmon.entities.WormholeEntity;
import com.pixelmonmod.pixelmon.entities.pixelmon.PixelmonEntity;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screen.MainMenuScreen;
import net.minecraft.client.renderer.texture.NativeImage;
import net.minecraft.entity.Entity;
import net.minecraft.entity.player.ServerPlayerEntity;
import net.minecraft.util.ResourceLocation;
import net.minecraft.util.ScreenShotHelper;
import net.minecraft.world.server.ServerWorld;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.server.ServerLifecycleHooks;
import xaero.hud.minimap.BuiltInHudModules;
import xaero.hud.minimap.radar.icon.RadarIconManager;
import xaero.hud.minimap.radar.icon.creator.RadarIconCreator;
import xaero.hud.minimap.radar.icon.definition.RadarIconDefinitionManager;
import xaero.hud.minimap.radar.icon.definition.form.sprite.RadarIconSpriteForm;
import xaero.common.icon.XaeroIcon;
import xaero.map.WorldMapSession;
import xaero.map.element.render.ElementRenderInfo;
import xaero.map.element.render.ElementRenderLocation;
import xaero.map.gui.GuiMap;
import xaero.map.pixelmon.WorldRadarGuard;
import xaero.pixelmon.PixelmonSprites;
import xaero.pixelmon.CompassHud;
import net.minecraft.item.ItemStack;
import net.minecraft.util.Hand;
import net.minecraft.util.math.BlockPos;
import net.minecraftforge.registries.ForgeRegistries;
import com.chaosthedude.naturescompass.items.NaturesCompassItem;
import com.chaosthedude.explorerscompass.items.ExplorersCompassItem;

/** Private isolated-world runtime QA. This JAR is never included in delivery. */
@Mod("mapcompat_qa")
public final class MapClientProbe {
    static volatile int state;
    static int ticks;
    static final long DEADLINE=System.nanoTime()+600_000_000_000L;
    static final Map<UUID,String> expected=new ConcurrentHashMap<>();
    static final List<Entity> oldEntities=new ArrayList<>();
    static final List<String> checks=new ArrayList<>();
    static void check(boolean value,String message){if(!value)throw new AssertionError(message);checks.add(message);System.out.println("MAP_QA_CHECK "+message);}
    static void result(String text){try{Files.writeString(Path.of("qa-result.txt"),text+"\n"+String.join("\n",checks));}catch(Exception e){e.printStackTrace();}System.out.println("MAP_QA_RESULT "+text);}
    static void fail(Throwable e){e.printStackTrace();state=-1;result("FAIL "+e);}
    static Object invoke(Object target,String name,Object...args){try{for(var m:target.getClass().getMethods())if(m.getName().equals(name)&&m.getParameterCount()==args.length)return m.invoke(target,args);throw new NoSuchMethodException(name);}catch(Exception e){throw new RuntimeException(e);}}
    static void cmd(ServerPlayerEntity p,String text){Object commands=invoke(ServerLifecycleHooks.getCurrentServer(),"func_195571_aL");invoke(commands,"func_197059_a",p.func_195051_bN().func_197033_a(4).func_197031_a(),text);}
    static void fixtures(ServerPlayerEntity p){
        expected.clear();ServerWorld w=(ServerWorld)p.field_70170_p;
        cmd(p,"gamemode creative");cmd(p,"tp @s 0.5 66 0.5");cmd(p,"gamerule doMobSpawning false");cmd(p,"kill @e[type=!minecraft:player]");
        cmd(p,"fill -20 63 -20 20 63 20 minecraft:grass_block");cmd(p,"time set day");
        if(StorageProxy.getParty(p).get(0)==null)StorageProxy.getParty(p).set(0,PokemonFactory.create(PixelmonSpecies.fromDex(25).orElseThrow()));
        int[] dex={25,25,6,658,1026,1025};String[] forms={"","","mega","ash_permanent","",""};
        for(int i=0;i<dex.length;i++){
            Pokemon mon=PokemonFactory.create(PixelmonSpecies.fromDex(dex[i]).orElseThrow());
            if(i==1)mon.setShiny(true);if(!forms[i].isEmpty())mon.setForm(forms[i]);
            PixelmonEntity e=new PixelmonEntity(w,mon);e.func_70012_b(-12+i*4,65,8,0,0);e.func_94061_f(true);w.func_217376_c(e);
            expected.put(e.func_110124_au(),dex[i]+":"+forms[i]+":"+(i==1));
        }
        WormholeEntity worm=new WormholeEntity(w,9,67,-8,100000);w.func_217376_c(worm);expected.put(worm.func_110124_au(),"wormhole");
        ItemStack nature=new ItemStack(ForgeRegistries.ITEMS.getValue(new ResourceLocation("naturescompass:naturescompass")));
        ItemStack explorer=new ItemStack(ForgeRegistries.ITEMS.getValue(new ResourceLocation("explorerscompass:explorerscompass")));
        nature.func_196082_o();explorer.func_196082_o();
        p.func_184611_a(Hand.MAIN_HAND,nature);p.func_184611_a(Hand.OFF_HAND,explorer);
        NaturesCompassItem ni=(NaturesCompassItem)nature.func_77973_b();ExplorersCompassItem ei=(ExplorersCompassItem)explorer.func_77973_b();
        if(w.func_234923_W_().func_240901_a_().toString().equals("minecraft:overworld"))ni.searchForBiome(w,p,new ResourceLocation("minecraft:plains"),new BlockPos(0,65,0),nature);
        else {ni.setSearching(nature,new ResourceLocation("minecraft:plains"),p);ni.setFound(nature,0,0,1,p);}
        ei.setSearching(explorer,new ResourceLocation("minecraft:village"),p);ei.setFound(explorer,12,-12,1,p);
    }
    @Mod.EventBusSubscriber(modid="mapcompat_qa")
    public static final class ServerEvents {
        @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e){
            if(e.phase!=TickEvent.Phase.END || (state!=10&&state!=11&&state!=13))return;
            var server=ServerLifecycleHooks.getCurrentServer();if(server==null)return;
            @SuppressWarnings("unchecked") List<ServerPlayerEntity> players=(List<ServerPlayerEntity>)invoke(invoke(server,"func_184103_al"),"func_181057_v");
            ServerPlayerEntity p=players.stream().findFirst().orElse(null);if(p==null)return;
            try{
                if(state==10){cmd(p,"execute in minecraft:overworld run tp @s 0.5 66 0.5");fixtures(p);state=2;}
                else if(state==11){cmd(p,"execute in pixelmon:ultra_space run tp @s 0.5 80 0.5");state=12;}
                else if(state==13){fixtures(p);state=14;}
            }catch(Throwable ex){fail(ex);}
        }
    }
    static boolean ready(Minecraft mc){
        var session=BuiltInHudModules.MINIMAP.getCurrentSession();
        return mc.field_71439_g!=null&&mc.field_71441_e!=null&&session!=null&&session.getWorldManager().getCurrentWorld()!=null
            &&mc.field_71441_e.func_234923_W_().equals(session.getWorldManager().getCurrentWorld().getDimId())&&WorldMapSession.getCurrentSession()!=null;
    }
    static ElementRenderInfo info(Minecraft mc,net.minecraft.util.RegistryKey<net.minecraft.world.World> key){
        return new ElementRenderInfo(ElementRenderLocation.fromIndex(0),mc.field_71439_g,mc.field_71439_g,mc.field_71439_g.func_213303_ch(),0,0,1,false,1,1,1,mc.func_147110_a(),1,key);
    }
    static void nativeIcons(Minecraft mc) throws Exception {
        List<Entity> entities=new ArrayList<>();for(Entity e:mc.field_71441_e.func_217416_b())if(expected.containsKey(e.func_110124_au()))entities.add(e);
        check(entities.size()==7,"Seven live synchronized fixture entities");
        RadarIconManager manager=new RadarIconManager(new RadarIconCreator());
        Map<String,String> sprites=new HashMap<>();
        for(Entity e:entities){
            String label=expected.get(e.func_110124_au());Object key=PixelmonSprites.variant(e);check(key instanceof String,"Sprite key "+label);
            if(e instanceof PixelmonEntity)check(key.equals(((PixelmonEntity)e).getSprite().toString()),"JourneyMap-identical sprite API "+label);
            sprites.put(label,key.toString());
            var def=new RadarIconDefinitionManager().get(net.minecraft.entity.EntityType.func_200718_a(e.func_200600_R()));
            check(def!=null&&def.getVariantForm(key.toString()) instanceof RadarIconSpriteForm,"Native dynamic sprite form "+label);
            check(((RadarIconSpriteForm)def.getVariantForm(key.toString())).getSpriteLocation().toString().equals(key),"Sprite resource unchanged "+label);
            try(var resource=mc.func_195551_G().func_199002_a(new ResourceLocation(key.toString()))){check(resource!=null,"Live texture exists "+label);}
            manager.allowPrerender();XaeroIcon rendered=manager.get(e,1f,false,false,mc.func_147110_a());
            check(rendered!=null&&rendered!=RadarIconManager.FAILED&&rendered!=RadarIconManager.DOT,"Native OpenGL icon rendered "+label);
            check(WorldRadarGuard.canRender(e,info(mc,mc.field_71441_e.func_234923_W_())),"Current-dimension entity accepted "+label);
        }
        check(!sprites.get("25::false").equals(sprites.get("25::true")),"Normal and shiny sprite cache keys differ");
        Files.writeString(Path.of("qa-sprites.txt"),sprites.toString());oldEntities.addAll(entities);manager.reset();
        check(xaero.common.settings.ModSettings.ENCHANT_COLORS.length==16,"Legacy compass field ABI restored");
        Class<?> bridge=Class.forName("com.chaosthedude.explorerscompass.connect.NewWayPoint");
        var callback=bridge.getMethod("addPoint",int.class,int.class,net.minecraft.entity.player.PlayerEntity.class,String.class);
        callback.invoke(null,12,-12,mc.field_71439_g,"地图适配验收");callback.invoke(null,12,-12,mc.field_71439_g,"地图适配验收");
        int count=0;for(var p:BuiltInHudModules.MINIMAP.getCurrentSession().getWorldManager().getCurrentWorld().getCurrentWaypointSet().getWaypoints())if(p.getName().equals("地图适配验收")&&p.getX()==12&&p.getZ()==-12)count++;
        check(count==1,"Actual transformed compass callback creates one saved marker, no duplicate or linkage error");
        ItemStack nature=mc.field_71439_g.func_184614_ca(),explorer=mc.field_71439_g.func_184592_cb();
        check(nature.func_77973_b() instanceof NaturesCompassItem&&explorer.func_77973_b() instanceof ExplorersCompassItem,"Both compass items synchronized in separate hands");
        check(((NaturesCompassItem)nature.func_77973_b()).getState(nature)==com.chaosthedude.naturescompass.util.CompassState.FOUND,"Nature compass biome search completed with Xaero and Explorer loaded");
        int offset=CompassHud.natureYOffset(5);check(offset>5,"Overlapping compass HUDs separated");
        mc.field_71439_g.func_184611_a(Hand.MAIN_HAND,explorer);mc.field_71439_g.func_184611_a(Hand.OFF_HAND,nature);
        check(CompassHud.natureYOffset(5)==offset,"HUD separation works with either compass in main hand");
        mc.field_71439_g.func_184611_a(Hand.MAIN_HAND,ItemStack.field_190927_a);
        check(CompassHud.natureYOffset(5)==5,"Nature compass alone keeps original HUD position");
        mc.field_71439_g.func_184611_a(Hand.MAIN_HAND,nature);mc.field_71439_g.func_184611_a(Hand.OFF_HAND,explorer);
        com.chaosthedude.naturescompass.gui.GuiWrapper.openGUI(mc.field_71441_e,mc.field_71439_g,nature);
        check(mc.field_71462_r instanceof com.chaosthedude.naturescompass.gui.NaturesCompassScreen,"Native Nature biome-selection screen opens");
        com.chaosthedude.explorerscompass.gui.GuiWrapper.openGUI(mc.field_71441_e,mc.field_71439_g,explorer);
        check(mc.field_71462_r instanceof com.chaosthedude.explorerscompass.gui.ExplorersCompassScreen,"Native Explorer structure-selection screen opens");
        mc.func_147108_a(null);
    }
    static void shot(Minecraft mc,String filename)throws Exception {
        try(NativeImage image=ScreenShotHelper.func_198052_a(mc.func_228018_at_().func_198105_m(),mc.func_228018_at_().func_198083_n(),mc.func_147110_a())){image.func_209270_a(Path.of(filename));}
    }
    static void openMap(Minecraft mc){mc.func_147108_a(new GuiMap(null,null,WorldMapSession.getCurrentSession().getMapProcessor(),mc.field_71439_g));}
    @Mod.EventBusSubscriber(modid="mapcompat_qa",value=Dist.CLIENT)
    public static final class ClientEvents {
        @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e){
            if(e.phase!=TickEvent.Phase.END||state<0)return;Minecraft mc=Minecraft.func_71410_x();
            try{
                if(System.nanoTime()>DEADLINE)throw new AssertionError("Client timeout at state "+state);
                if(state==0&&mc.field_71462_r instanceof MainMenuScreen){state=1;ticks=0;mc.func_238191_a_("map-compat-qa");}
                else if(state==1&&mc.field_71439_g!=null&&mc.field_71441_e!=null){mc.func_147108_a(null);if(++ticks>60){ticks=0;state=10;}}
                else if(state==2&&++ticks>100&&ready(mc)){
                    mc.func_147108_a(null);nativeIcons(mc);shot(mc,"qa-minimap-overworld.png");openMap(mc);state=3;ticks=0;
                }else if(state==3&&++ticks>50){shot(mc,"qa-worldmap-overworld.png");mc.func_147108_a(null);state=11;ticks=0;}
                else if(state==12&&ready(mc)&&mc.field_71441_e.func_234923_W_().func_240901_a_().toString().equals("pixelmon:ultra_space")&&++ticks>60){
                    check(true,"Native client and both map sessions entered Ultra Space");
                    for(Entity old:oldEntities)check(!WorldRadarGuard.canRender(old,info(mc,mc.field_71441_e.func_234923_W_())),"Old-dimension entity rejected after wormhole-world transition");
                    oldEntities.clear();state=13;ticks=0;
                }else if(state==14&&ready(mc)&&++ticks>100){mc.func_147108_a(null);nativeIcons(mc);shot(mc,"qa-minimap-ultraspace.png");openMap(mc);state=15;ticks=0;}
                else if(state==15&&++ticks>40){shot(mc,"qa-worldmap-ultraspace.png");if(mc.field_71441_e!=null)mc.field_71441_e.func_72882_A();mc.func_213231_b(new MainMenuScreen());mc.func_147108_a(new MainMenuScreen());state=16;ticks=0;}
                else if(state==16&&mc.field_71441_e==null&&mc.func_71401_C()==null&&++ticks>30){check(!WorldRadarGuard.sessionReady(),"Radar session blocked while disconnected");mc.func_238191_a_("map-compat-qa");state=17;ticks=0;}
                else if(state==17&&ready(mc)&&++ticks>80){check(true,"World reconnect and map sessions reinitialized");mc.func_147108_a(null);shot(mc,"qa-reconnect.png");result("PASS "+checks.size()+" runtime checks");state=18;ticks=0;}
                else if(state==18&&++ticks>15){state=-2;mc.func_71400_g();}
            }catch(Throwable ex){fail(ex);}
        }
    }
}
