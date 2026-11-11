// Anchor the tip of each sport marker to the venue's exact coordinates.
export function sportMarkerOptions(sport:string){
 if(!['football','table_tennis','billiards'].includes(sport))return {preset:'islands#blueSportIcon'};
 return {
  iconLayout:'default#image',
  iconImageHref:`${import.meta.env.BASE_URL}markers/${sport}.svg`,
  iconImageSize:[48,58],
  iconImageOffset:[-24,-54],
 };
}
