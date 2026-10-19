package mapcompat.qa;

import com.google.gson.*;
import java.nio.file.*;
import java.util.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screen.MainMenuScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.server.ServerLifecycleHooks;
import xaero.hud.minimap.BuiltInHudModules;
import xaero.map.WorldMapSession;
import xaero.map.gui.GuiMap;
import com.pixelmonmod.pixelmon.api.pokemon.PokemonFactory;
import com.pixelmonmod.pixelmon.api.registries.PixelmonSpecies;
import com.pixelmonmod.pixelmon.entities.pixelmon.PixelmonEntity;
import xaero.hud.minimap.radar.icon.RadarIconManager;
import xaero.hud.minimap.radar.icon.creator.RadarIconCreator;

/** Native reader integration test, private disposable instance only. */
@Mod("mapcompat_qa")
public final class MapClientProbe {
    static volatile int state;
    static int ticks,checks;
    static final Map<UUID,Boolean> caps=new java.util.concurrent.ConcurrentHashMap<>();
    static final long DEADLINE=System.nanoTime()+360_000_000_000L;
    static void check(boolean b,String text){if(!b)throw new AssertionError(text);checks++;System.out.println("MIGRATION_QA_CHECK "+text);}
    static void verify(Minecraft mc,String dimension)throws Exception {
        JsonArray expected=new JsonParser().parse(Files.readString(Path.of("migration-native-expected.json"))).getAsJsonArray();
        var world=BuiltInHudModules.MINIMAP.getCurrentSession().getWorldManager().getCurrentWorld();
        check(world.getDimId().func_240901_a_().toString().equals(dimension),"Native waypoint dimension "+dimension);
        int total=0;
        for(JsonElement el:expected){
            JsonObject p=el.getAsJsonObject();if(!p.get("dimension").getAsString().equals(dimension))continue;
            int count=0;
            for(var w:world.getCurrentWaypointSet().getWaypoints()){
                if(!w.getName().equals(p.get("name").getAsString())||w.getX()!=p.get("x").getAsInt()||w.getZ()!=p.get("z").getAsInt())continue;
                check(w.getY()==p.get("y").getAsInt(),"Exact imported Y "+w.getName());
                check(w.isDisabled()==p.get("disabled").getAsBoolean(),"Imported enabled flag "+w.getName());
                check(w.getPurpose().isDeath()==p.get("death").getAsBoolean(),"Native historical death purpose "+w.getName());
                count++;
            }
            check(count==1,"One native loaded marker "+p.get("name").getAsString());total++;
        }
        check(total>0,"Expected fixtures present in "+dimension);
    }
    static boolean ready(Minecraft mc,String dim){
        var session=BuiltInHudModules.MINIMAP.getCurrentSession();
        return mc.field_71441_e!=null&&mc.field_71439_g!=null&&session!=null&&session.getWorldManager().getCurrentWorld()!=null
            &&mc.field_71441_e.func_234923_W_().func_240901_a_().toString().equals(dim)
            &&session.getWorldManager().getCurrentWorld().getDimId().equals(mc.field_71441_e.func_234923_W_())&&WorldMapSession.getCurrentSession()!=null;
    }
    static void customSprites(Minecraft mc)throws Exception{
        var manager=new RadarIconManager(new RadarIconCreator());Set<String> locations=new HashSet<>();int seen=0;
        for(var e:mc.field_71441_e.func_217416_b())if(caps.containsKey(e.func_110124_au())){
            var mon=(PixelmonEntity)e;String path=mon.getSprite().toString();locations.add(path);
            check(path.startsWith("pixelmon_backport:"),"Custom CapPikachu resource namespace shiny="+caps.get(e.func_110124_au()));
            check(path.equals(xaero.pixelmon.PixelmonSprites.variant(mon)),"Custom actual sprite selected unchanged");
            try(var resource=mc.func_195551_G().func_199002_a(mon.getSprite())){check(resource!=null,"Custom sprite exists");}
            manager.allowPrerender();var icon=manager.get(mon,1f,false,false,mc.func_147110_a());
            check(icon!=null&&icon!=RadarIconManager.DOT&&icon!=RadarIconManager.FAILED,"Custom normal/shiny native GL icon rendered");seen++;
        }
        check(seen==2&&locations.size()==2,"Custom CapPikachu normal and shiny have distinct sprites");manager.reset();
    }
    static Object invoke(Object target,String name,Object...args)throws Exception{
        for(var m:target.getClass().getMethods())if(m.getName().equals(name)&&m.getParameterCount()==args.length)return m.invoke(target,args);
        throw new NoSuchMethodException(name);
    }
    static void teleport(String dim)throws Exception{
        var server=ServerLifecycleHooks.getCurrentServer();if(server==null)return;
        var list=(List<?>)invoke(invoke(server,"func_184103_al"),"func_181057_v");if(list.isEmpty())return;
        var p=(net.minecraft.entity.player.ServerPlayerEntity)list.get(0);
        invoke(invoke(server,"func_195571_aL"),"func_197059_a",p.func_195051_bN().func_197033_a(4).func_197031_a(),"execute in "+dim+" run tp @s 0.5 66 0.5");
        if(dim.equals("minecraft:overworld"))for(boolean shiny:new boolean[]{false,true}){
            var pokemon=PokemonFactory.create(PixelmonSpecies.fromDex(1026).orElseThrow());pokemon.setShiny(shiny);
            var entity=new PixelmonEntity(p.field_70170_p,pokemon);entity.func_70012_b(shiny?5:2,66,8,0,0);entity.func_94061_f(true);
            p.field_70170_p.func_217376_c(entity);caps.put(entity.func_110124_au(),shiny);
        }
    }
    @Mod.EventBusSubscriber(modid="mapcompat_qa")
    public static class ServerEvents{
        @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e){
            if(e.phase!=TickEvent.Phase.END)return;
            try{if(state==10){teleport("minecraft:overworld");state=2;ticks=0;}else if(state==11){teleport("pixelmon:ultra_space");state=4;ticks=0;}}
            catch(Throwable ex){fail(ex);}
        }
    }
    static void fail(Throwable ex){ex.printStackTrace();state=-1;try{Files.writeString(Path.of("migration-native-result.txt"),"FAIL "+ex);}catch(Exception ignored){}}
    @Mod.EventBusSubscriber(modid="mapcompat_qa",value=Dist.CLIENT)
    public static class ClientEvents{
        @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e){
            if(e.phase!=TickEvent.Phase.END||state<0)return;Minecraft mc=Minecraft.func_71410_x();
            try{
                if(System.nanoTime()>DEADLINE)throw new AssertionError("Migration client timeout state "+state);
                if(state==0&&mc.field_71462_r instanceof MainMenuScreen){state=1;mc.func_238191_a_("map-compat-qa");}
                else if(state==1&&mc.field_71439_g!=null&&++ticks>50){state=10;ticks=0;}
                else if(state==2&&ready(mc,"minecraft:overworld")&&++ticks>70){
                    verify(mc,"minecraft:overworld");customSprites(mc);mc.func_147108_a(new GuiMap(null,null,WorldMapSession.getCurrentSession().getMapProcessor(),mc.field_71439_g));state=3;ticks=0;
                }else if(state==3&&++ticks>40){check(mc.field_71462_r instanceof GuiMap,"Native big map accepts imported markers");mc.func_147108_a(null);state=11;ticks=0;}
                else if(state==4&&ready(mc,"pixelmon:ultra_space")&&++ticks>70){verify(mc,"pixelmon:ultra_space");Files.writeString(Path.of("migration-native-result.txt"),"PASS "+checks+" native migration checks\n");state=5;ticks=0;}
                else if(state==5&&++ticks>10){state=-2;mc.func_71400_g();}
            }catch(Throwable ex){fail(ex);}
        }
    }
}
